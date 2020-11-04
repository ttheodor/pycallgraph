import networkx as nx
from itertools import chain
from collections import defaultdict
from copy import deepcopy
from operator import itemgetter


class CallGraph:
    def __init__(self):
        self.cg = nx.MultiDiGraph()
        self.related_edges = defaultdict(set)

    def __copy(self):
        c = CallGraph()
        c.cg = self.cg.copy()
        c.related_edges = deepcopy(self.related_edges)
        return c

    def number_edges(self):
        return self.cg.number_of_edges()

    def relate_edges(self, e1, e2):
        if e1 == e2:
            return
        self.related_edges[e1].add(e2)
        self.related_edges[e2].add(e1)

    def unrelate_edges(self, e1, e2):
        if e1 == e2:
            return
        self.related_edges[e1].discard(e2)
        if not self.related_edges[e1]:
            self.related_edges.pop(e1, None)

        self.related_edges[e2].discard(e1)
        if not self.related_edges[e2]:
            self.related_edges.pop(e2, None)

    def drop_edge_from_relations(self, e):
        for re in self.get_related_edges(e):
            self.unrelate_edges(e, re)

    def get_related_edges(self, e):
        return list(self.related_edges[e])

    def add_edge(self, e):
        self.cg.add_edge(e[0], e[1])

    def add_edges(self, es):
        self.cg.add_edges_from(es)

    def drop_edges_from_callers_with_many_callees(self, threshold):
        edges_to_drop = []
        for n, d in self.cg.out_degree():
            if d <= threshold:
                continue
            edges_to_drop.extend(self.cg.out_edges(n))
        self.cg.remove_edges_from(edges_to_drop)
        for e in edges_to_drop:
            for re in self.get_related_edges(e):
                self.unrelate_edges(e, re)

    def bridges(self):
        edges = []
        for u, v in nx.bridges(nx.Graph(self.cg)):
            if self.cg.number_of_edges(u, v) > 1:
                continue
            if not self.cg.has_edge(u, v):
                u, v = v, u
            for k in self.cg[u][v].keys():
                edges.append((u, v, k))
        return edges

    def least_eccentric_edge(self, edges=None):
        if edges is None:
            edges = self.cg.edges
        ecc = nx.eccentricity(self.cg.to_undirected(),
                              set(chain.from_iterable(edges)))
        return min(
            (((n1, n2, k), max(ecc[n1], ecc[n2])) for n1, n2, k in edges),
            key=itemgetter(1))[0]

    def merge_edge(self, e, copy=True):
        u, v, k = e
        assert self.cg.has_edge(u, v)

        ncg = self.__copy() if copy else self
        ncg.drop_edge(e, copy=False)

        for v1, n, k1 in list(ncg.cg.out_edges(v, keys=True)):
            nk = ncg.cg.add_edge(u, n)
            ncg.relate_edges((v1, n, k1), (u, n, nk))
            for e in ncg.get_related_edges((v1, n, k1)):
                ncg.relate_edges((u, n, nk), e)

        if ncg.cg.in_degree(v) == 0:
            for e in ncg.cg.edges(v, keys=True):
                ncg.drop_edge_from_relations(e)

            ncg.cg.remove_node(v)

        if copy:
            return ncg

    def drop_edge(self, e, copy=True):
        ncg = self.__copy() if copy else self
        ncg.cg.remove_edge(e[0], e[1], e[2])

        edges_to_drop = ncg.get_related_edges(e)
        ncg.cg.remove_edges_from(edges_to_drop)
        for o in edges_to_drop:
            ncg.unrelate_edges(e, o)

        if copy:
            return ncg

    def __make_components(self, ccs):
        for cc in ccs:
            ncg = CallGraph()
            ncg.cg = cc.copy()
            ncg.related_edges = deepcopy(self.related_edges)
            for e in self.cg.edges:
                if not ncg.cg.has_edge(e[0], e[1]):
                    ncg.drop_edge_from_relations(e)
            yield ncg

    def directed_components(self):
        return self.__make_components(
            (nx.subgraph(self.cg, nx.dfs_tree(self.cg, source=n))
             for n, d in self.cg.in_degree() if d == 0))

    def undirected_components(self):
        return self.__make_components(
            (nx.subgraph(self.cg, cc)
             for cc in nx.connected_components(self.cg.to_undirected())))
