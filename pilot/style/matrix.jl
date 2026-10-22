# Category x style matrix analysis (Julia, stdlib only).
# Rows = role categories (top: compute/io/glue; sub: numeric, collections, logic, filesystem, network, compose; leaf: intent),
# columns = programming styles. Model: z[intent, style] = mu + a[intent] + v[style] + interaction.
using LinearAlgebra, Statistics, DelimitedFiles, Random

const STYLES = ["P", "O", "F", "D", "G"]
cosine(a, b) = dot(a, b) / (norm(a) * norm(b) + 1e-12)
nearest(q, C) = argmax([cosine(q, C[k, :]) for k in 1:size(C, 1)])

struct Data
    G::Array{Float64,3}             # intent x style x d
    intents::Vector{String}; top::Vector{String}; sub::Vector{String}
    Zr::Matrix{Float64}; mr::Matrix{String}
end

function load(model, var)
    Z = readdlm("jl/$(model)_$(var)_ds.tsv", '\t', Float64)
    meta = readdlm("jl/meta_ds.tsv", '\t', String)
    intents = unique(meta[:, 1]); nI = length(intents); d = size(Z, 2)
    G = zeros(nI, 5, d); top = String[]; sub = String[]
    for (i, it) in enumerate(intents)
        rows = findall(==(it), meta[:, 1]); push!(top, meta[rows[1], 2]); push!(sub, meta[rows[1], 3])
        for r in rows; G[i, findfirst(==(meta[r, 4]), STYLES), :] = Z[r, :]; end
    end
    Data(G, intents, top, sub, readdlm("jl/$(model)_$(var)_real.tsv", '\t', Float64), readdlm("jl/meta_real.tsv", '\t', String))
end

rowsmean(G, idx) = dropdims(mean(G[idx, :, :], dims = (1, 2)), dims = (1, 2))

# style vectors: per-intent centering over styles, then mean over intents
function stylevecs(G, idx)
    X = G[idx, :, :]; X = X .- mean(X, dims = 2)
    return dropdims(mean(X, dims = 1), dims = 1)       # 5 x d
end
function stylebasis(V)
    Vc = V .- mean(V, dims = 1); F = svd(Vc); return F.Vt[1:4, :]   # 4 x d
end

# ---- variance decomposition (hierarchy of row effects) --------------------
function variance_shares(D::Data)
    G = D.G; nI = size(G, 1); mu = mean(G, dims = (1, 2)); X = G .- mu
    a = mean(X, dims = 2); v = mean(X, dims = 1); inter = X .- a .- v
    A = dropdims(a, dims = 2)                                        # nI x d
    tmean = Dict(t => mean(A[D.top .== t, :], dims = 1) for t in unique(D.top))
    smean = Dict(s => mean(A[D.sub .== s, :], dims = 1) for s in unique(D.sub))
    T = vcat([tmean[D.top[i]] for i in 1:nI]...); Sb = vcat([smean[D.sub[i]] for i in 1:nI]...)
    tot = sum(abs2, X)
    return Dict("top_category" => 5sum(abs2, T) / tot, "sub_given_top" => 5sum(abs2, Sb .- T) / tot,
                "intent_given_sub" => 5sum(abs2, A .- Sb) / tot, "style" => nI * sum(abs2, v) / tot, "interaction" => sum(abs2, inter) / tot)
end

# ---- leave-one-intent-out category classification --------------------------
function loio_category(D::Data, labels::Vector{String}; correct_style::Bool = false)
    G = D.G; nI = size(G, 1); hits = 0; n = 0
    for b in 1:nI
        tr = [i for i in 1:nI if i != b]; cats = unique(labels[tr])
        V = stylevecs(G, tr)
        C = vcat([rowsmean(G, tr[labels[tr] .== c])' for c in cats]...)        # style-averaged category centroids
        for s in 1:5
            q = G[b, s, :]; correct_style && (q = q .- V[s, :])
            hits += cats[nearest(q, C)] == labels[b]; n += 1
        end
    end
    return hits / n
end
function perm_p(D, labels; reps = 200, seed = 1)
    rng = MersenneTwister(seed); obs = loio_category(D, labels); null = Float64[]
    for _ in 1:reps; push!(null, loio_category(D, shuffle(rng, labels))); end
    return obs, mean(null), (1 + count(>=(obs), null)) / (reps + 1)
end

# ---- leave-one-intent-out style identification ------------------------------
# mode :intent_centered (needs the intent's other styles), :global (subtract global mean only),
# :true_sub (subtract the true sub-category centroid of TRAIN intents), :pred_sub (predict sub-category first)
function loio_style(D::Data, mode::Symbol)
    G = D.G; nI = size(G, 1); hits = 0; n = 0
    for b in 1:nI
        tr = [i for i in 1:nI if i != b]; V = stylevecs(G, tr); B = stylebasis(V); P = V * B'
        gm = rowsmean(G, tr); subs = unique(D.sub[tr])
        C = vcat([rowsmean(G, tr[D.sub[tr] .== c])' for c in subs]...)
        for s in 1:5
            z = G[b, s, :]
            base = mode == :intent_centered ? dropdims(mean(G[b, :, :], dims = 1), dims = 1) :
                   mode == :global ? gm :
                   mode == :true_sub ? (D.sub[b] in subs ? rowsmean(G, tr[D.sub[tr] .== D.sub[b]]) : gm) :
                   (C[nearest(z, C), :])
            c = B * (z - base); hits += argmin([sum(abs2, c - P[k, :]) for k in 1:5]) == s; n += 1
        end
    end
    return hits / n
end

# ---- is the style offset shared across categories? --------------------------
function style_vec_consistency(D::Data)
    tops = unique(D.top); out = Dict{String,Float64}()
    Vs = Dict(t => stylevecs(D.G, findall(==(t), D.top)) for t in tops)
    for i in 1:length(tops), j in i+1:length(tops)
        out["cos($(tops[i]),$(tops[j]))"] = mean([cosine(Vs[tops[i]][s, :], Vs[tops[j]][s, :]) for s in 1:5])
    end
    return out
end
# cross-category analogy: z(b,s) ~ z(b,r) + mean_{a in pool}(z(a,s)-z(a,r)); pool = same sub / other category / all others
function analogy(D::Data, pool::Symbol)
    G = D.G; nI = size(G, 1); hits = 0; n = 0
    for b in 1:nI
        P = pool == :same_sub ? [a for a in 1:nI if a != b && D.sub[a] == D.sub[b]] :
            pool == :other_top ? [a for a in 1:nI if D.top[a] != D.top[b]] : [a for a in 1:nI if a != b]
        isempty(P) && continue
        for s in 1:5, r in 1:5
            r == s && continue
            pred = G[b, r, :] .+ dropdims(mean(G[P, s, :] .- G[P, r, :], dims = 1), dims = 1)
            cand = [t for t in 1:5 if t != r]
            hits += cand[argmax([dot(pred, G[b, t, :]) for t in cand])] == s; n += 1
        end
    end
    return hits / n
end

function auroc(pos, neg)  # P(score_pos > score_neg), ties 0.5
    s = 0.0; for p in pos, q in neg; s += p > q ? 1.0 : (p == q ? 0.5 : 0.0); end; s / (length(pos) * length(neg))
end

# ---- real code: nearest (category x style) cell, style coordinates, outlier check
function real_code(D::Data, outprefix)
    G = D.G; nI = size(G, 1); idx = collect(1:nI); V = stylevecs(G, idx); B = stylebasis(V)
    tops = unique(D.top); subs = unique(D.sub)
    Ctop = vcat([rowsmean(G, findall(==(t), D.top))' for t in tops]...)
    Csub = vcat([rowsmean(G, findall(==(t), D.sub))' for t in subs]...)
    # cell prototypes (top x style)
    cells = Matrix{Float64}(undef, length(tops) * 5, size(G, 3)); lab = Tuple{Int,Int}[]
    for (ti, t) in enumerate(tops), s in 1:5
        cells[(ti - 1) * 5 + s, :] = dropdims(mean(G[D.top .== t, s, :], dims = 1), dims = 1); push!(lab, (ti, s))
    end
    corps = unique(D.mr[:, 1]); res = Dict{String,Any}()
    Zr = D.Zr; nR = size(Zr, 1)
    topP = [tops[nearest(Zr[k, :], Ctop)] for k in 1:nR]; subP = [subs[nearest(Zr[k, :], Csub)] for k in 1:nR]
    cellP = [lab[nearest(Zr[k, :], cells)] for k in 1:nR]
    coords = zeros(nR, 4)
    for k in 1:nR; coords[k, :] = B * (Zr[k, :] - Ctop[findfirst(==(topP[k]), tops), :]); end
    open("$(outprefix)_real_coords.tsv", "w") do io
        for k in 1:nR
            println(io, join([D.mr[k, 1], D.mr[k, 2], D.mr[k, 3], topP[k], subP[k], tops[cellP[k][1]], STYLES[cellP[k][2]], coords[k, :]...], '\t'))
        end
    end
    summary = Dict{String,Any}()
    for c in corps
        r = findall(==(c), D.mr[:, 1]); exp_top = D.mr[r[1], 2]; exp_sub = D.mr[r[1], 3]
        s = Dict{String,Any}("n" => length(r),
            "top_share" => Dict(t => round(count(==(t), topP[r]) / length(r), digits = 2) for t in tops),
            "sub_share" => Dict(t => round(count(==(t), subP[r]) / length(r), digits = 2) for t in subs),
            "style_share" => Dict(STYLES[k] => round(count(x -> x[2] == k, cellP[r]) / length(r), digits = 2) for k in 1:5))
        exp_top != "-" && (s["top_acc"] = count(==(exp_top), topP[r]) / length(r))
        exp_sub != "-" && (s["sub_acc"] = count(==(exp_sub), subP[r]) / length(r))
        cen = mean(coords[r, :], dims = 1); s["spread"] = mean([norm(coords[k, :] - vec(cen)) for k in r])
        # consistency/outlier: centroid from first half of this corpus; own held-out half vs all other corpora
        rng = MersenneTwister(0); rr = shuffle(rng, r); h = length(rr) ÷ 2; fit = rr[1:h]; te = rr[h+1:end]
        m = vec(mean(coords[fit, :], dims = 1)); oth = findall(!=(c), D.mr[:, 1])
        s["outlier_auroc"] = auroc([norm(coords[k, :] - m) for k in oth], [norm(coords[k, :] - m) for k in te])
        summary[c] = s
    end
    return summary
end

function main(model, var)
    D = load(model, var); out = Dict{String,Any}()
    out["variance"] = variance_shares(D)
    out["top_acc"] = perm_p(D, D.top); out["sub_acc"] = perm_p(D, D.sub)
    out["top_acc_style_corrected"] = loio_category(D, D.top; correct_style = true)
    out["sub_acc_style_corrected"] = loio_category(D, D.sub; correct_style = true)
    out["style_acc"] = Dict(String(m) => loio_style(D, m) for m in (:global, :intent_centered, :true_sub, :pred_sub))
    out["style_vec_cos_between_tops"] = style_vec_consistency(D)
    out["analogy_row_acc"] = Dict(String(p) => analogy(D, p) for p in (:same_sub, :other_top, :all))
    out["real"] = real_code(D, "out/$(model)_$(var)")
    return out
end

function show(io, x, ind = 0)
    pad = "  " ^ ind
    if x isa Dict
        for k in sort(collect(keys(x)); by = string); v = x[k]
            if v isa Dict; println(io, pad, k, ":"); show(io, v, ind + 1) else println(io, pad, k, ": ", v isa Tuple ? map(y -> round(y, digits = 3), v) : (v isa Float64 ? round(v, digits = 3) : v)) end
        end
    end
end

if abspath(PROGRAM_FILE) == @__FILE__
    for model in ARGS, var in ("raw", "hashed")
        isfile("jl/$(model)_$(var)_ds.tsv") || continue
        open("out/$(model)_$(var).txt", "w") do io; show(io, main(model, var)); end
        println("done ", model, " ", var)
    end
end
