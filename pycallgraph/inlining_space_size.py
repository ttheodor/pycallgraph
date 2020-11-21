from operator import itemgetter

def naive_inlining_space_size(cg):
    return 2**cg.number_edges()


def undirected_partitioned_inlining_space_size(cg):
    s = sum(2**cc.number_edges() for cc in cg.undirected_components()
            if cc.number_edges() > 0)
    return s if s > 0 else 1


def directed_connected_components_inlining_space_size(cg):
    s = sum(2**cc.number_edges() for cc in cg.directed_components()
            if cc.number_edges() > 0)
    return s if s > 0 else 1


def recursive_inlining_space_size(cg, directed=True):
    if cg.number_edges() == 0:
        return 1
    if cg.number_edges() == 1:
        return 2

    ccs = list(cg.undirected_components())
    if len(ccs) > 1:
        return sum(recursive_inlining_space_size(cc) for cc in ccs)

    if directed:
        dccs = list(cg.directed_components())
        if len(dccs) > 1:
            return sum(recursive_inlining_space_size(cc) for cc in dccs)

    bridges = cg.bridges()
    if bridges:
        e = cg.least_eccentric_edge(bridges)
    else:
        u = max(cg.cg.out_degree(), key=itemgetter(1))[0]
        es = list(cg.cg.out_edges(u, keys=True))
        v = min(cg.cg.in_degree(v for _, v, _ in es), key=itemgetter(1))[0]
        e = next(filter(lambda e: e[0] == u and e[1] == v, es))

    cg_e_dropped = cg.drop_edge(e, copy=True)
    cg_e_merged = cg.merge_edge(e, copy=True)

    return recursive_inlining_space_size(
        cg_e_merged) + recursive_inlining_space_size(cg_e_dropped)
