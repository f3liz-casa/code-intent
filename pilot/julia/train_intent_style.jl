# Intent -> style prior, trained in Julia (stdlib only).
#
# Model: a small MLP maps the Intent features of a unit (layer, effect category, name verb, reachable leaves, language)
# to a diagonal Gaussian over its name-free style features:  y ~ N(mu(x), diag(exp(s(x)))).
# Loss = Gaussian negative log-likelihood (+ L2), Adam, hand-written backprop (checked against finite differences).
# The held-out NLL of a unit under this prior says how unusual its style is *for its Intent*; it never says better or worse.
#
# usage: julia train_intent_style.jl <data dir from export_intent_style.py> <out dir> [--check] [--epochs N] [--hidden H]
using LinearAlgebra, Statistics, DelimitedFiles, Random, Printf

# ---------------------------------------------------------------- data
struct Data
    X::Matrix{Float64}      # d_in x n
    Y::Matrix{Float64}      # d_out x n, standardized style features
    meta::Matrix{String}    # n x 8: file line cls name layer cat lang fold
    xcols::Vector{String}
    ycols::Vector{String}
end

function load_data(dir)
    X = Matrix(readdlm(joinpath(dir, "intent_X.tsv"), '\t', Float64)')
    Y = Matrix(readdlm(joinpath(dir, "style_Y.tsv"), '\t', Float64)')
    meta = readdlm(joinpath(dir, "unit_meta.tsv"), '\t', String, quotes = false)
    xcols = readlines(joinpath(dir, "intent_cols.txt"))
    ycols = String.(readdlm(joinpath(dir, "style_cols.tsv"), '\t', Any, quotes = false)[:, 1])
    @assert size(X, 2) == size(Y, 2) == size(meta, 1)
    Data(X, Y, meta, xcols, ycols)
end

# ---------------------------------------------------------------- model
mutable struct Net
    W1::Matrix{Float64}; b1::Vector{Float64}   # hidden
    W2::Matrix{Float64}; b2::Vector{Float64}   # mean head
    W3::Matrix{Float64}; b3::Vector{Float64}   # log-variance head
end

function Net(d_in, h, d_out; rng = Random.default_rng())
    Net(0.1 .* randn(rng, h, d_in), zeros(h), 0.1 .* randn(rng, d_out, h), zeros(d_out), 0.01 .* randn(rng, d_out, h), zeros(d_out))
end

# Log-variance is squashed into [SLO, SHI]. The floor matters: many style features are rare (a unit almost never uses .then or switch),
# so an unconstrained variance head collapses to ~0 on them and every non-zero value later scores as an astronomical outlier.
const SLO, SHI = log(0.25^2), 2.0
const SMID, SHALF = (SHI + SLO) / 2, (SHI - SLO) / 2
squash(a) = SMID + SHALF * tanh(a / SHALF)
dsquash(a) = 1 - tanh(a / SHALF)^2

function forward(m::Net, X)
    H = tanh.(m.W1 * X .+ m.b1)
    MU = m.W2 * H .+ m.b2
    A = m.W3 * H .+ m.b3
    return H, MU, A
end

# mean NLL per unit (sum over style features) and the gradient of  loss = mean_n( sum_d 0.5 (s + (y-mu)^2 e^-s) ) + wd/2 |W|^2
function loss_grad(m::Net, X, Y, wd)
    n = size(X, 2)
    H, MU, A = forward(m, X)
    S = squash.(A)
    R = Y .- MU
    E = exp.(-S)
    nll = sum(0.5 .* (S .+ R .^ 2 .* E)) / n
    dMU = -(R .* E) ./ n
    dS = 0.5 .* (1 .- R .^ 2 .* E) ./ n
    dA = dS .* dsquash.(A)
    dH = m.W2' * dMU + m.W3' * dA
    dZ = dH .* (1 .- H .^ 2)
    g = (dW1 = dZ * X' + wd .* m.W1, db1 = vec(sum(dZ, dims = 2)),
         dW2 = dMU * H' + wd .* m.W2, db2 = vec(sum(dMU, dims = 2)),
         dW3 = dA * H' + wd .* m.W3, db3 = vec(sum(dA, dims = 2)))
    reg = 0.5 * wd * (sum(abs2, m.W1) + sum(abs2, m.W2) + sum(abs2, m.W3))
    return nll + reg, g
end

params(m::Net) = (m.W1, m.b1, m.W2, m.b2, m.W3, m.b3)
grads(g) = (g.dW1, g.db1, g.dW2, g.db2, g.dW3, g.db3)

function gradcheck(rng)
    m = Net(7, 5, 3; rng = rng); X = randn(rng, 7, 20); Y = randn(rng, 3, 20)
    _, g = loss_grad(m, X, Y, 1e-3)
    worst = 0.0
    for (P, G) in zip(params(m), grads(g)), _ in 1:4
        i = rand(rng, 1:length(P)); old = P[i]; ε = 1e-6
        P[i] = old + ε; lp, _ = loss_grad(m, X, Y, 1e-3)
        P[i] = old - ε; lm, _ = loss_grad(m, X, Y, 1e-3)
        P[i] = old
        worst = max(worst, abs((lp - lm) / (2ε) - G[i]) / (abs(G[i]) + 1e-8 + abs((lp - lm) / (2ε))))
    end
    return worst
end

# Early stopping on a validation set: the NLL of a heteroscedastic model is dominated by rare features, so the number of epochs
# matters a lot (12 epochs and 60 epochs differ by a factor of 4 in held-out NLL); the best epoch is kept.
function train!(m::Net, X, Y; epochs = 80, batch = 128, lr = 3e-3, wd = 1e-3, rng = Random.default_rng(), verbose = false, val = nothing)
    best = (Inf, deepcopy(m), 0)
    ps = collect(params(m)); M = [zero(p) for p in ps]; V = [zero(p) for p in ps]; t = 0
    n = size(X, 2)
    for ep in 1:epochs
        perm = randperm(rng, n)
        for s in 1:batch:n
            idx = perm[s:min(s + batch - 1, n)]
            _, g = loss_grad(m, X[:, idx], Y[:, idx], wd)
            t += 1
            for (k, G) in enumerate(grads(g))
                M[k] .= 0.9 .* M[k] .+ 0.1 .* G
                V[k] .= 0.999 .* V[k] .+ 0.001 .* G .^ 2
                ps[k] .-= lr .* (M[k] ./ (1 - 0.9^t)) ./ (sqrt.(V[k] ./ (1 - 0.999^t)) .+ 1e-8)
            end
        end
        if val !== nothing
            vl = mean(score(m, val[1], val[2])[1])
            vl < best[1] && (best = (vl, deepcopy(m), ep))
        end
        if verbose && (ep % 10 == 0 || ep == 1)
            l, _ = loss_grad(m, X, Y, 0.0); @printf("  epoch %3d  train nll %.3f%s\n", ep, l, val === nothing ? "" : @sprintf("  val nll %.3f", mean(score(m, val[1], val[2])[1])))
        end
    end
    if val !== nothing
        for (P, Q) in zip(params(m), params(best[2])); P .= Q; end
        verbose && @printf("  kept epoch %d (val nll %.3f)\n", best[3], best[1])
    end
    return m
end

# per-unit NLL and standardized residuals
function score(m::Net, X, Y)
    _, MU, A = forward(m, X)
    S = squash.(A)
    Z = (Y .- MU) .* exp.(-S ./ 2)
    nll = vec(sum(0.5 .* (S .+ (Y .- MU) .^ 2 .* exp.(-S)), dims = 1))
    return nll, Z, MU
end

# ---------------------------------------------------------------- baselines: Gaussian per group, shrunk toward the global one
function group_gaussian(keys_tr, Ytr, keys_te, Yte; k0 = 5.0)
    gm = vec(mean(Ytr, dims = 2)); gv = max.(vec(var(Ytr, dims = 2)), exp(SLO))
    st = Dict{String,Tuple{Int,Vector{Float64},Vector{Float64}}}()
    for key in unique(keys_tr)
        idx = findall(==(key), keys_tr); n = length(idx)
        mu = vec(mean(Ytr[:, idx], dims = 2)); v = n > 1 ? vec(var(Ytr[:, idx], dims = 2)) : gv
        w = n / (n + k0)
        st[key] = (n, w .* mu .+ (1 - w) .* gm, max.(w .* v .+ (1 - w) .* gv, exp(SLO)))
    end
    nll = zeros(length(keys_te))
    for (j, key) in enumerate(keys_te)
        mu, v = haskey(st, key) ? (st[key][2], st[key][3]) : (gm, gv)
        nll[j] = sum(0.5 .* (log.(v) .+ (Yte[:, j] .- mu) .^ 2 ./ v))
    end
    return nll
end

# ---------------------------------------------------------------- main
function main(args)
    dir, out = args[1], args[2]; mkpath(out)
    flag(name, default) = (i = findfirst(==(name), args); i === nothing ? default : parse(typeof(default), args[i+1]))
    epochs = flag("--epochs", 40); hidden = flag("--hidden", 48)
    rng = MersenneTwister(0)
    if "--check" in args
        @printf("gradient check, worst relative error: %.2e\n", gradcheck(rng))
    end
    D = load_data(dir)
    n = size(D.X, 2); dI, dO = size(D.X, 1), size(D.Y, 1)
    fold = parse.(Int, D.meta[:, 8])
    layer = D.meta[:, 5]; cat = D.meta[:, 6]
    keyed = Dict("global" => fill("all", n), "layer" => layer, "layer+category" => layer .* "|" .* cat)
    oof_nll = zeros(n); oof_Z = zeros(dO, n); oof_MU = zeros(dO, n)
    base = Dict(k => zeros(n) for k in keys(keyed))
    for f in 0:4
        te = findall(==(f), fold); va = findall(==(mod(f + 1, 5)), fold); tr = findall(x -> x != f && x != mod(f + 1, 5), fold)
        m = train!(Net(dI, hidden, dO; rng = rng), D.X[:, tr], D.Y[:, tr]; epochs = epochs, rng = rng, verbose = (f == 0), val = (D.X[:, va], D.Y[:, va]))
        tr = vcat(tr, va)
        nll, Z, MU = score(m, D.X[:, te], D.Y[:, te])
        oof_nll[te] = nll; oof_Z[:, te] = Z; oof_MU[:, te] = MU
        for (k, keys) in keyed
            base[k][te] = group_gaussian(keys[tr], D.Y[:, tr], keys[te], D.Y[:, te])
        end
        @printf("fold %d: n_test=%d  MLP prior %.3f  layer+category %.3f  layer %.3f  global %.3f\n", f, length(te), mean(nll), mean(base["layer+category"][te]), mean(base["layer"][te]), mean(base["global"][te]))
    end

    open(joinpath(out, "results.txt"), "w") do io
        println(io, "held-out NLL per unit (sum over $(dO) standardized style features; lower = style better predicted by the Intent)")
        @printf(io, "  global Gaussian          %.3f\n", mean(base["global"]))
        @printf(io, "  per layer                %.3f\n", mean(base["layer"]))
        @printf(io, "  per layer+category       %.3f\n", mean(base["layer+category"]))
        @printf(io, "  MLP Intent prior         %.3f\n", mean(oof_nll))
        println(io, "\nR^2 of the MLP mean per style feature (held out, vs predicting the training mean):")
        for j in 1:dO
            r2 = 1 - sum((D.Y[j, :] .- oof_MU[j, :]) .^ 2) / sum((D.Y[j, :] .- mean(D.Y[j, :])) .^ 2)
            @printf(io, "  %-10s %6.3f\n", D.ycols[j], r2)
        end
        println(io, "\nmost unusual styles for their Intent (highest held-out NLL), with the three features that deviate most (z):")
        for i in sortperm(oof_nll, rev = true)[1:25]
            top = sortperm(abs.(oof_Z[:, i]), rev = true)[1:3]
            desc = join([@sprintf("%s %+.1f", D.ycols[j], oof_Z[j, i]) for j in top], ", ")
            @printf(io, "  %7.1f  %s:%s %s.%s  [%s/%s]  %s\n", oof_nll[i], replace(D.meta[i, 1], r"^packages/" => ""), D.meta[i, 2], D.meta[i, 3], D.meta[i, 4], D.meta[i, 5], D.meta[i, 6], desc)
        end
    end
    open(joinpath(out, "unit_scores.tsv"), "w") do io
        println(io, "file\tline\tclass\tname\tlayer\tcategory\theldout_nll")
        for i in 1:n; println(io, join([D.meta[i, 1:6]..., @sprintf("%.3f", oof_nll[i])], '\t')); end
    end

    # final model on all units, weights as TSV so other tools can load them
    va = findall(==(0), fold); tr = findall(!=(0), fold)
    m = train!(Net(dI, hidden, dO; rng = rng), D.X[:, tr], D.Y[:, tr]; epochs = epochs, rng = rng, val = (D.X[:, va], D.Y[:, va]))
    for (nm, P) in zip(("W1", "b1", "W2", "b2", "W3", "b3"), params(m))
        writedlm(joinpath(out, "model_$(nm).tsv"), P, '\t')
    end
    println(read(joinpath(out, "results.txt"), String))
end

if abspath(PROGRAM_FILE) == (@__FILE__)
    main(ARGS)
end
