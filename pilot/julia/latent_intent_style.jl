# Learn the derivation of Intent (category) and a few clear styles, with no hand-written leaf table or category rules.
#
# Generative model per unit i (layer l):
#   category c ~ pi_l(c)                     (a learned "topic": what the unit is for)
#   tokens   w ~ Multinomial(phi_c)          (callee tokens and name words, from export_tokens.py)
#   style    s ~ rho_{l,c}(s)                (a learned style, a small set of prototypes)
#   y        ~ N(mu_s, diag(sigma2_s))       (17 name-free structure features, standardized)
# Fitted by EM (stdlib only). Sparsity: a Dirichlet(alpha < 1) prior on rho (MAP-EM, rows are allowed to drop styles to zero)
# and pruning of styles that carry too few units, so that few, clear styles stay.
#
# usage: julia latent_intent_style.jl <data dir (export_intent_style.py + export_tokens.py)> <out dir> [--kc 12] [--ks 10] [--alpha 0.5]
using LinearAlgebra, Statistics, DelimitedFiles, Random, Printf

const VFLOOR = 0.25^2
# Rare habits (a unit that uses .then once) are far in the tail of a standardized feature. Every style density is therefore a
# contamination model per feature: (1-EPS) N(mu, s2) + EPS N(mu, TAU2). Without it a style that never sees .then scores a
# real .then at hundreds of nats and the mixture ends up worse than one global Gaussian.
const EPS, TAU2 = 0.02, 100.0
function rlogpdf(y, mu, s2)
    a = log(1 - EPS) - 0.5 * (log(2π * s2) + (y - mu)^2 / s2)
    b = log(EPS) - 0.5 * (log(2π * TAU2) + (y - mu)^2 / TAU2)
    return a > b ? a + log1p(exp(b - a)) : b + log1p(exp(a - b))
end

struct Data
    n::Int; V::Int; L::Int
    layer::Vector{Int}; layers::Vector{String}
    hand::Vector{String}                  # hand-written category, used only to *evaluate* the learned one
    Y::Matrix{Float64}                    # n x d standardized style features
    ycols::Vector{String}; ymu::Vector{Float64}; ysd::Vector{Float64}
    I::Vector{Int}; W::Vector{Int}; C::Vector{Float64}
    vocab::Vector{String}
    fold::Vector{Int}
    meta::Matrix{String}
end

function load_data(dir)
    meta = readdlm(joinpath(dir, "unit_meta.tsv"), '\t', String, quotes = false)
    Y = Matrix(readdlm(joinpath(dir, "style_Y.tsv"), '\t', Float64))
    sc = readdlm(joinpath(dir, "style_cols.tsv"), '\t', Any, quotes = false)
    tk = readdlm(joinpath(dir, "tokens_sparse.tsv"), '\t', Int)
    vocab = readlines(joinpath(dir, "tokens_vocab.txt"))
    layers = sort(unique(meta[:, 5]))
    Data(size(Y, 1), length(vocab), length(layers), [findfirst(==(l), layers) for l in meta[:, 5]], layers, meta[:, 6], Y,
         String.(sc[:, 1]), Float64.(sc[:, 2]), Float64.(sc[:, 3]), tk[:, 1], tk[:, 2], Float64.(tk[:, 3]), vocab,
         parse.(Int, meta[:, 8]), meta)
end

mutable struct Model
    Kc::Int; Ks::Int
    pi::Matrix{Float64}        # L x Kc
    phi::Matrix{Float64}       # Kc x V
    rho::Array{Float64,3}      # L x Kc x Ks
    mu::Matrix{Float64}        # Ks x d
    s2::Matrix{Float64}        # Ks x d
end

logsumexp(v) = (m = maximum(v); m + log(sum(exp.(v .- m))))

# token log-likelihood per unit and category  (n x Kc)
function token_ll(m::Model, I, W, C, n)
    T = zeros(n, m.Kc); lphi = log.(m.phi)
    @inbounds for t in eachindex(I), c in 1:m.Kc
        T[I[t], c] += C[t] * lphi[c, W[t]]
    end
    return T
end

# style log-density per unit and style  (n x Ks)
function style_ll(m::Model, Y)
    G = zeros(size(Y, 1), m.Ks)
    for s in 1:m.Ks, i in 1:size(Y, 1)
        v = 0.0
        for j in 1:size(Y, 2); v += rlogpdf(Y[i, j], m.mu[s, j], m.s2[s, j]); end
        G[i, s] = v
    end
    return G
end

# posterior over categories from layer and tokens only (what the model can *derive* without seeing style)
function category_post(m::Model, T, layer)
    P = zeros(length(layer), m.Kc)
    for i in eachindex(layer)
        lp = log.(m.pi[layer[i], :]) .+ T[i, :]
        P[i, :] = exp.(lp .- logsumexp(lp))
    end
    return P
end

# held-out negative log density of y given layer and tokens: sum_c p(c|l,w) sum_s rho_lcs N(y|s)
function heldout_nll(m::Model, d::Data, idx)
    T = token_ll(m, d.I, d.W, d.C, d.n); G = style_ll(m, d.Y)
    out = zeros(length(idx))
    for (k, i) in enumerate(idx)
        l = d.layer[i]; lp = log.(m.pi[l, :]) .+ T[i, :]; post = exp.(lp .- logsumexp(lp))
        terms = [log(post[c] + 1e-300) + logsumexp(log.(m.rho[l, c, :] .+ 1e-300) .+ G[i, :]) for c in 1:m.Kc]
        out[k] = -logsumexp(terms)
    end
    return out
end

function fit(d::Data, idx; Kc = 12, Ks = 10, alpha = 0.5, kappa = 2.0, beta = 0.01, iters = 60, prune = 0.02, rng = MersenneTwister(0), verbose = false)
    n = length(idx); dy = size(d.Y, 2); L = d.L; Ytr = d.Y[idx, :]
    # init: styles at random units, categories random responsibilities
    mu = d.Y[idx[randperm(rng, n)[1:Ks]], :]; s2 = ones(Ks, dy)
    m = Model(Kc, Ks, fill(1 / Kc, L, Kc), fill(1 / d.V, Kc, d.V), fill(1 / Ks, L, Kc, Ks), mu, s2)
    inT = Dict(i => k for (k, i) in enumerate(idx))
    ti = [t for t in eachindex(d.I) if haskey(inT, d.I[t])]
    R = rand(rng, n, Kc); R ./= sum(R, dims = 2)
    alive = trues(Ks)
    for it in 1:iters
        # M-step for categories from current responsibilities R (n x Kc)
        m.pi .= 1e-3; for (k, i) in enumerate(idx); m.pi[d.layer[i], :] .+= R[k, :]; end
        m.pi ./= sum(m.pi, dims = 2)
        m.phi .= beta; for t in ti; k = inT[d.I[t]]; m.phi[:, d.W[t]] .+= d.C[t] .* R[k, :]; end
        m.phi ./= sum(m.phi, dims = 2)
        # E-step
        T = token_ll(m, d.I, d.W, d.C, d.n); G = style_ll(m, d.Y)
        N = zeros(L, Kc, Ks); Rs = zeros(n, Ks); Rnew = zeros(n, Kc); wsum = zeros(Ks); ll = 0.0
        for (k, i) in enumerate(idx)
            l = d.layer[i]; lp = zeros(Kc, Ks)
            for c in 1:Kc, s in 1:Ks
                lp[c, s] = alive[s] ? log(m.pi[l, c]) + T[i, c] + log(m.rho[l, c, s] + 1e-300) + G[i, s] : -Inf
            end
            z = logsumexp(vec(lp)); ll += z
            r = exp.(lp .- z); @views N[l, :, :] .+= r; Rnew[k, :] = sum(r, dims = 2); Rs[k, :] = vec(sum(r, dims = 1))
        end
        R = Rnew
        # M-step for styles
        wsum = vec(sum(Rs, dims = 1))
        for s in 1:Ks
            alive[s] || continue
            m.mu[s, :] = vec(sum(Rs[:, s] .* Ytr, dims = 1)) ./ (wsum[s] + 1e-9)
            for j in 1:dy
                m.s2[s, j] = max(sum(Rs[:, s] .* (Ytr[:, j] .- m.mu[s, j]) .^ 2) / (wsum[s] + 1e-9), VFLOOR)
            end
        end
        # sparse Dirichlet MAP for rho: rows may drop styles; back off to the layer's own style mix
        for l in 1:L
            Nl = vec(sum(N[l, :, :], dims = 1)); back = (Nl .+ 1e-9) ./ sum(Nl .+ 1e-9)
            for c in 1:Kc
                v = max.(N[l, c, :] .+ kappa .* back .+ (alpha - 1), 1e-9); v[.!alive] .= 0
                m.rho[l, c, :] = v ./ sum(v)
            end
        end
        # prune styles that carry too few units (after a burn-in)
        if it > 15 && it % 5 == 0
            for s in 1:Ks
                if alive[s] && wsum[s] / n < prune && count(alive) > 2
                    alive[s] = false
                end
            end
        end
        verbose && (it % 15 == 0 || it == 1) && @printf("  iter %2d  loglik/unit %.3f  styles alive %d\n", it, ll / n, count(alive))
    end
    return m, alive
end

# normalized mutual information between two labelings
function nmi(a, b)
    n = length(a); ua = unique(a); ub = unique(b)
    pa = Dict(x => count(==(x), a) / n for x in ua); pb = Dict(x => count(==(x), b) / n for x in ub)
    mi = 0.0
    for x in ua, y in ub
        pxy = count(i -> a[i] == x && b[i] == y, 1:n) / n
        pxy > 0 && (mi += pxy * log(pxy / (pa[x] * pb[y])))
    end
    ha = -sum(p * log(p) for p in values(pa)); hb = -sum(p * log(p) for p in values(pb))
    return 2mi / (ha + hb + 1e-12)
end

function main(args)
    dir, out = args[1], args[2]; mkpath(out)
    flag(name, default) = (i = findfirst(==(name), args); i === nothing ? default : parse(typeof(default), args[i+1]))
    Kc = flag("--kc", 12); Ks = flag("--ks", 10); alpha = flag("--alpha", 0.5)
    d = load_data(dir); n = d.n
    io = open(joinpath(out, "latent_results.txt"), "w")
    say(s...) = (println(s...); println(io, s...))
    say("held-out NLL of style features given layer and tokens (5 folds grouped by file); Kc=$Kc categories, Ks<=$Ks styles")
    say(@sprintf("  reference from sec. 29: MLP on hand-built Intent features 3.67, per layer+category (hand) 6.65, global Gaussian 8.58"))
    # baselines with the same robust density: one Gaussian per group, shrunk to the global one
    function group_nll(keys)
        nll = zeros(n)
        for f in 0:4
            tr = findall(!=(f), d.fold); te = findall(==(f), d.fold)
            gm = vec(mean(d.Y[tr, :], dims = 1)); gv = max.(vec(var(d.Y[tr, :], dims = 1)), VFLOOR)
            for key in unique(keys[te])
                ix = tr[keys[tr] .== key]; w = length(ix) / (length(ix) + 5.0)
                mu = length(ix) > 1 ? w .* vec(mean(d.Y[ix, :], dims = 1)) .+ (1 - w) .* gm : gm
                v = length(ix) > 1 ? max.(w .* vec(var(d.Y[ix, :], dims = 1)) .+ (1 - w) .* gv, VFLOOR) : gv
                for i in te[keys[te] .== key]; nll[i] = -sum(rlogpdf(d.Y[i, j], mu[j], v[j]) for j in 1:size(d.Y, 2)); end
            end
        end
        return mean(nll)
    end
    say(@sprintf("  %-34s NLL %.3f", "global Gaussian (robust)", group_nll(fill("all", n))))
    say(@sprintf("  %-34s NLL %.3f", "per layer (robust)", group_nll(d.meta[:, 5])))
    say(@sprintf("  %-34s NLL %.3f", "per layer + HAND category (robust)", group_nll(d.meta[:, 5] .* "|" .* d.hand)))
    configs = [("dense, no pruning (alpha=1)", 1.0, 0.0, Ks), ("sparse prior alpha=$alpha, prune <2%", alpha, 0.02, Ks), ("3 styles", 1.0, 0.0, 3), ("5 styles", 1.0, 0.0, 5), ("8 styles", 1.0, 0.0, 8)]
    for (label, a, pr, ks) in configs
        nll = zeros(n); alive_counts = Int[]; nmis = Float64[]
        for f in 0:4
            tr = findall(!=(f), d.fold); te = findall(==(f), d.fold)
            m, alive = fit(d, tr; Kc = Kc, Ks = ks, alpha = a, prune = pr, rng = MersenneTwister(f))
            nll[te] = heldout_nll(m, d, te); push!(alive_counts, count(alive))
            T = token_ll(m, d.I, d.W, d.C, n); P = category_post(m, T, d.layer)
            push!(nmis, nmi([argmax(P[i, :]) for i in te], d.hand[te]))
        end
        say(@sprintf("  %-34s NLL %.3f   styles alive %.1f   NMI(learned category, hand category) %.2f", label, mean(nll), mean(alive_counts), mean(nmis)))
    end

    # final fit on everything with the sparse prior: describe what was learned
    m, alive = fit(d, collect(1:n); Kc = Kc, Ks = Ks, alpha = alpha, prune = 0.02, rng = MersenneTwister(0), verbose = true)
    T = token_ll(m, d.I, d.W, d.C, n); P = category_post(m, T, d.layer); cat_id = [argmax(P[i, :]) for i in 1:n]
    G = style_ll(m, d.Y)
    sty = [argmax([alive[s] ? log(sum(m.pi[d.layer[i], c] * m.rho[d.layer[i], c, s] for c in 1:m.Kc) + 1e-300) + G[i, s] : -Inf for s in 1:m.Ks]) for i in 1:n]
    say("\nLEARNED STYLES (alive ones, by share):")
    order = sortperm([count(==(s), sty) for s in 1:m.Ks], rev = true); cum = 0.0
    for s in order
        alive[s] || continue
        k = count(==(s), sty); k == 0 && continue; cum += k / n
        z = m.mu[s, :]; top = sortperm(abs.(z), rev = true)[1:4]
        raw = [@sprintf("%s %s%.1f", d.ycols[j], z[j] > 0 ? "+" : "-", abs(z[j])) for j in top]
        ls = sort(collect(Dict(l => count(i -> sty[i] == s && d.layer[i] == l, 1:n) for l in 1:d.L)), by = x -> -x[2])[1:3]
        say(@sprintf("  style %-2d %5.1f%% (cum %5.1f%%)  %s   | layers: %s", s, 100k / n, 100cum, join(raw, ", "), join([@sprintf("%s %d", d.layers[l], c) for (l, c) in ls], ", ")))
    end
    say("\nLEARNED CATEGORIES (size, top tokens by lift, hand-category mix):")
    bg = vec(sum(m.phi .* (sum(P, dims = 1)'), dims = 1)) ./ sum(P)
    for c in sortperm([count(==(c), cat_id) for c in 1:m.Kc], rev = true)
        k = count(==(c), cat_id); k == 0 && continue
        lift = [m.phi[c, w] * log((m.phi[c, w] + 1e-12) / (bg[w] + 1e-12)) for w in 1:d.V]
        toks = d.vocab[sortperm(lift, rev = true)[1:8]]
        hm = sort(collect(Dict(h => count(i -> cat_id[i] == c && d.hand[i] == h, 1:n) for h in unique(d.hand))), by = x -> -x[2])[1:2]
        say(@sprintf("  cat %-2d n=%4d  %s   | hand: %s", c, k, join(toks, " "), join([@sprintf("%s %d", h, v) for (h, v) in hm], ", ")))
    end
    close(io)
    open(joinpath(out, "latent_units.tsv"), "w") do f
        println(f, "file\tline\tname\tlayer\thand_category\tlearned_category\tlearned_style")
        for i in 1:n; println(f, join([d.meta[i, 1], d.meta[i, 2], d.meta[i, 4], d.meta[i, 5], d.hand[i], cat_id[i], sty[i]], '\t')); end
    end
end

if abspath(PROGRAM_FILE) == (@__FILE__)
    main(ARGS)
end
