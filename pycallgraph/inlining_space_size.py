def naive_inlining_space_size(cg):
    return 2**cg.number_edges()


def undirected_partitioned_inlining_space_size(cg):
    s = sum(2**cc.number_edges() for cc in cg.undirected_components())
    return s if s > 0 else 1


def directed_connected_components_inlining_space_size(cg):
    s = sum(2**cc.number_edges() for cc in cg.directed_components())
    return s if s > 0 else 1


def recursive_inlining_space_size(cg, directed=True):
    if cg.number_edges() == 0:
        return 0
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
    e = cg.least_eccentric_edge(bridges if bridges else None)

    cg_e_dropped = cg.drop_edge(e, copy=True)
    cg_e_merged = cg.merge_edge(e, copy=True)

    return recursive_inlining_space_size(
        cg_e_merged) + recursive_inlining_space_size(cg_e_dropped)
