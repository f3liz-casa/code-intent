# Train the latent category/style model on the multi-language corpus and report what is shared across languages.
# Held-out = whole repositories (fold 0 of export_corpus.py). Layers are language:role buckets shared across repositories.
#
# usage: julia corpus_train.jl <data dir from export_corpus.py> <out dir> [--kc 24] [--ks 12] [--iters 40]
using LinearAlgebra, Statistics, DelimitedFiles, Random, Printf
include(joinpath(@__DIR__, "latent_intent_style.jl"))

function main_corpus(args)
    dir, out = args[1], args[2]; mkpath(out)
    flag(name, default) = (i = findfirst(==(name), args); i === nothing ? default : parse(typeof(default), args[i+1]))
    Kc = flag("--kc", 24); Ks = flag("--ks", 12); iters = flag("--iters", 40)
    d = load_data(dir); n = d.n
    lang = d.meta[:, 7]; langs = sort(unique(lang)); repo = size(d.meta, 2) >= 9 ? d.meta[:, 9] : fill("?", n)
    tr = findall(!=(0), d.fold); te = findall(==(0), d.fold)
    io = open(joinpath(out, "corpus_results.txt"), "w"); say(s...) = (println(s...); println(io, s...))
    say(@sprintf("%d units, %d repositories, %d languages, %d layers, %d tokens; train %d units, held-out %d units from %d repositories",
                 n, length(unique(repo)), length(langs), d.L, d.V, length(tr), length(te), length(unique(repo[te]))))
    say("units per language: " * join([@sprintf("%s %d", l, count(==(l), lang)) for l in langs], ", "))

    # baselines with the same robust density: global, and per language:role layer
    function base_nll(keys)
        gm = vec(mean(d.Y[tr, :], dims = 1)); gv = max.(vec(var(d.Y[tr, :], dims = 1)), VFLOOR)
        st = Dict{String,Tuple{Vector{Float64},Vector{Float64}}}()
        for key in unique(keys[tr])
            ix = tr[keys[tr] .== key]; w = length(ix) / (length(ix) + 5.0)
            st[key] = length(ix) > 1 ? (w .* vec(mean(d.Y[ix, :], dims = 1)) .+ (1 - w) .* gm, max.(w .* vec(var(d.Y[ix, :], dims = 1)) .+ (1 - w) .* gv, VFLOOR)) : (gm, gv)
        end
        [begin mu, v = get(st, keys[i], (gm, gv)); -sum(rlogpdf(d.Y[i, j], mu[j], v[j]) for j in 1:size(d.Y, 2)) end for i in te]
    end
    g = base_nll(fill("all", n)); pl = base_nll(d.meta[:, 5])
    say(@sprintf("\nheld-out NLL (repositories never seen in training): global %.3f, per language:role layer %.3f", mean(g), mean(pl)))
    results = Dict{String,Vector{Float64}}("global" => g, "layer" => pl)
    models = Dict{String,Tuple{Model,BitVector}}()
    for (label, alpha, prune) in (("dense", 1.0, 0.0), ("sparse", 0.5, 0.02))
        m, alive = fit(d, tr; Kc = Kc, Ks = Ks, alpha = alpha, prune = prune, iters = iters, rng = MersenneTwister(0), verbose = true)
        results[label] = heldout_nll(m, d, te); models[label] = (m, alive)
        say(@sprintf("  %-7s categories %d, styles alive %d: held-out NLL %.3f", label, Kc, count(alive), mean(results[label])))
    end
    say("\nheld-out NLL by language (global / layer / dense / sparse):")
    for l in langs
        ix = findall(==(l), lang[te]); isempty(ix) && continue
        say(@sprintf("  %-11s n=%6d  %.2f / %.2f / %.2f / %.2f", l, length(ix), mean(results["global"][ix]), mean(results["layer"][ix]), mean(results["dense"][ix]), mean(results["sparse"][ix])))
    end

    # what was learned (sparse model on all units)
    m, alive = models["sparse"]
    T = token_ll(m, d.I, d.W, d.C, n); G = style_ll(m, d.Y)
    sty = zeros(Int, n); cat = zeros(Int, n)
    for i in 1:n
        l = d.layer[i]; lp = log.(m.pi[l, :]) .+ T[i, :]; post = exp.(lp .- logsumexp(lp)); cat[i] = argmax(post)
        sty[i] = argmax([alive[s] ? log(sum(post[c] * m.rho[l, c, s] for c in 1:m.Kc) + 1e-300) + G[i, s] : -Inf for s in 1:m.Ks])
    end
    bylang(ids) = (c = Dict{String,Int}(); for i in ids; c[lang[i]] = get(c, lang[i], 0) + 1; end; sort(collect(c), by = x -> -x[2]))
    say("\nLEARNED STYLES (share; strongest features; language mix; share of the dominant language = how local the style is):")
    cum = 0.0
    for s in sortperm([count(==(s), sty) for s in 1:m.Ks], rev = true)
        alive[s] || continue; ids = findall(==(s), sty); isempty(ids) && continue; cum += length(ids) / n
        top = sortperm(abs.(m.mu[s, :]), rev = true)[1:4]; lm = bylang(ids)
        say(@sprintf("  style %-2d %5.1f%% (cum %5.1f%%)  %s | %s | dominant %.0f%%", s, 100 * length(ids) / n, 100cum,
            join([@sprintf("%s %s%.1f", d.ycols[j], m.mu[s, j] > 0 ? "+" : "-", abs(m.mu[s, j])) for j in top], ", "),
            join([@sprintf("%s %.0f%%", l, 100c / length(ids)) for (l, c) in lm[1:min(4, end)]], ", "), 100 * lm[1][2] / length(ids)))
    end
    say("\nLEARNED CATEGORIES (size; top tokens by lift; language mix):")
    bg = vec(sum(m.phi .* (sum([cat[i] == c ? 1.0 : 0.0 for i in 1:n, c in 1:m.Kc], dims = 1)'), dims = 1)) ./ n
    for c in sortperm([count(==(c), cat) for c in 1:m.Kc], rev = true)
        ids = findall(==(c), cat); isempty(ids) && continue
        lift = [m.phi[c, w] * log((m.phi[c, w] + 1e-12) / (bg[w] + 1e-12)) for w in 1:d.V]
        say(@sprintf("  cat %-2d n=%6d  %s | %s", c, length(ids), join(d.vocab[sortperm(lift, rev = true)[1:8]], " "), join([@sprintf("%s %.0f%%", l, 100c2 / length(ids)) for (l, c2) in bylang(ids)[1:min(3, end)]], ", ")))
    end
    close(io)
    writedlm(joinpath(out, "style_means.tsv"), hcat(1:m.Ks, round.(m.mu, digits = 3)), '\t')
end

if abspath(PROGRAM_FILE) == (@__FILE__)
    main_corpus(ARGS)
end
