from collections import defaultdict
from operator import itemgetter


class InliningDecision:
    def __init__(self, e, choice):
        self.edge = (e[0], e[1], e[2])
        self.choice = choice

    def __str__(self):
        return f'{self.edge}, {self.choice}'

    def __repr__(self):
        return f'{self.edge}, {self.choice}'

    def __hash__(self):
        return hash((self.edge, self.choice))

    def __eq__(self, other):
        return self.edge == other.edge and self.choice == other.choice


def generate_configurations_recursive_ccs(ccs, decisions):
    yield decisions + [
        ('icc', [list(generate_configurations_recursive(cc)) for cc in ccs])
    ]


def generate_configurations_recursive(cg, decisions=[]):
    if cg.number_edges() == 0:
        yield decisions
        return
    if cg.number_edges() == 1:
        e = cg.edge_cc(cg.edges()[0])
        yield decisions + [InliningDecision(e, True)]
        yield decisions + [InliningDecision(e, False)]
        return

    ccs = list(cg.undirected_components())
    if len(ccs) > 1:
        ccs = [cc for cc in ccs if cc.number_edges() > 0]
        assert len(ccs) > 0
        if len(ccs) == 1:
            cg = ccs[0]
        else:
            yield from generate_configurations_recursive_ccs(ccs, decisions)
            return

    bridges = cg.bridges()
    e = cg.least_eccentric_edge(bridges if bridges else None)

    cg_e_dropped = cg.drop_edge(e, copy=True)
    cg_e_merged = cg.merge_edge(e, copy=True)

    e_cc = cg.edge_cc(e)

    yield from generate_configurations_recursive(
        cg_e_dropped, decisions + [InliningDecision(e_cc, False)])
    yield from generate_configurations_recursive(
        cg_e_merged, decisions + [InliningDecision(e_cc, True)])


def validate_configuration_structure(conf):
    if isinstance(conf, tuple):
        assert conf[0] == 'icc'
        for cc in conf[1]:
            validate_configuration_structure(conf[1])
        return
    assert isinstance(conf, list)
    for i, d in enumerate(conf):
        if isinstance(d, InliningDecision):
            continue
        if isinstance(d, tuple):
            assert i == len(conf) - 1
            validate_configuration_structure(d)


icc_tag = 0


def generate_candidates_from_config(conf, decisions=[]):
    global icc_tag
    if not conf:
        yield decisions
        return

    if isinstance(conf, tuple):
        assert conf[0] == 'icc'
        for icc in conf[1]:
            icc_tag_local = icc_tag
            icc_tag += 1
            for cc_alternative in icc:
                yield from generate_candidates_from_config(
                    cc_alternative, decisions + [('icc_tag', icc_tag_local)])
        return

    if isinstance(conf[-1], tuple):
        decisions = decisions + conf[:-1]
        yield from generate_candidates_from_config(conf[-1], decisions)
    else:
        yield decisions + conf


class ComponentDecisions:
    def __init__(self):
        self.decisions = dict()
        self.component_tags = []
        self.component_decisions = defaultdict(set)

    def __str__(self):
        return f'decisions: {self.decisions}\ncomponent tags: {self.component_tags}\ncomponent_decisions: {self.component_decisions}'

    def __repr__(self):
        return self.__str__()

    def add_component_tag(self, i):
        self.component_tags.append(i)

    def add_decision(self, d):
        self.decisions[d.edge] = d.choice
        if self.component_tags:
            self.component_decisions[self.component_tags[-1]].add(d.edge)

    def get_component_decisions(self, cc):
        assert cc in self.component_tags
        return [(d, self.decisions[d]) for d in self.component_decisions[cc]]

    def generate_decisions(self, all_ccs):
        def decision(cc):
            if cc in self.decisions:
                return self.decisions[cc]
            return False

        return [{
            'caller': cc[0],
            'callee': cc[1],
            'key': cc[2],
            'inline': decision(cc)
        } for cc in all_ccs]




def convert_candidate_to_component_decisions(cand):
    cds = ComponentDecisions()
    for e in cand:
        if isinstance(e, tuple):
            assert e[0] == 'icc_tag'
            cds.add_component_tag(e[1])
        else:
            cds.add_decision(e)
    return cds

class TreeNode:
    def __init__(self):
        self.children = []
        self.id = None
        self.score = None

    def merge_evaluated(self, scores):
        replace = []
        for i, c in enumerate(self.children):
            c = c.merge_evaluated(scores)
            if c is not None:
                replace.append((i, c))
        for i, c in replace:
            self.children[i] = c

    def generate_leaf_candidates(self, decisions):
        if not self.children:
            if self.score is None:
                yield (self.id, decisions)
        else:
            for c in self.children:
                yield from c.generate_leaf_candidates(decisions)

    def enumerate(self, id=0):
        self.id = id
        for c in self.children:
            id = c.enumerate(id + 1)

        return id

    def append(self, other):
        self.children.append(other)

    def __repr__(self, level):
        repr = '' if self.id is None else f'({self.id})'
        repr += '' if self.score == None else f'({self.score})'
        for c in self.children:
            repr += '\n' + c.__repr__(level + 1)
        return repr


class DecisionNode(TreeNode):
    def __init__(self, decisions):
        super().__init__()
        self.decisions = decisions

    def merge_evaluated(self, scores):
        if self.id in scores:
            assert self.score is None
            self.score = scores[self.id]
        super().merge_evaluated(scores)
        if all(isinstance(c, DecisionNode) for c in self.children):
            for c in self.children:
                self.decisions.extend(c.decisions)
            self.children.clear()

    def generate_leaf_candidates(self, decisions=[]):
        yield from super().generate_leaf_candidates(decisions + self.decisions)

    def __repr__(self, level=0):
        return '  ' * level + 'DecisionNode(' + str(
            self.decisions) + '):' + super().__repr__(level + 1)


class IccNode(TreeNode):
    def __init__(self):
        super().__init__()

    def merge_evaluated(self, scores):
        if all(c.id in scores or c.score is not None for c in self.children):

            def get_score(c):
                if c.score:
                    return c.score
                else:
                    return scores[c.id]

            best, score = min(((c, get_score(c)) for c in self.children),
                              key=itemgetter(1))
            best.score = score
            return best
        else:
            super().merge_evaluated(scores)

    def __repr__(self, level=0):
        return '  ' * level + 'IccNode' + super().__repr__(level + 1)


class IccParentNode(TreeNode):
    def __init__(self):
        super().__init__()

    def select_best_configuration(self, scores):
        return min((c.select_best_configuration for c in self.children),
                   key=itemgetter(1))

    def merge_evaluated(self, scores):
        replace = []
        for i, c in enumerate(self.children):
            c = c.merge_evaluated(scores)
            if c is not None:
                replace.append((i, c))
        for i, c in replace:
            self.children[i] = c

        if all(c.score is not None and isinstance(c, DecisionNode)
               for c in self.children):
            decisions = []
            for c in self.children:
                decisions.extend(c.decisions)
            replacement = DecisionNode(decisions)
            replacement.id = self.id
            return replacement

    def add_icc_node(self):
        icc = IccNode()
        self.append(icc)
        return icc

    def __repr__(self, level=0):
        return '  ' * level + 'IccParentNode' + super().__repr__(level + 1)


def make_tree_node(config):
    assert config

    if isinstance(config, tuple):
        assert config[0] == 'icc'
        icc_parent = IccParentNode()
        for icc in config[1]:
            icc_node = icc_parent.add_icc_node()
            for cc_alternative in icc:
                icc_node.append(make_tree_node(cc_alternative))
        return icc_parent

    if isinstance(config[-1], tuple):
        d_node = DecisionNode(config[:-1])
        d_node.append(make_tree_node(config[-1]))
        return d_node
    else:
        assert isinstance(config, list)
        return DecisionNode(config)


class ConfigTree:
    def __init__(self, config):
        self.root = make_tree_node(config)
        self.root.enumerate()
        self.final_decisions = None
        self.final_score = None

    def generate_leaf_candidates(self):
        assert self.final_decisions is None
        return list(self.root.generate_leaf_candidates())

    def merge_evaluated(self, scores):
        self.root.merge_evaluated(scores)
        if isinstance(self.root, DecisionNode) and self.root.score is not None:
            self.final_decisions = self.root.decisions
            self.final_score = self.root.score


    def candidates_remaining(self):
        return self.final_decisions is None

    def select_best_configuration(self):
        config, _ = root.select_best_configuration(scores)
        return config

    def __repr__(self):
        if self.final_decisions is None:
            return self.root.__repr__()
        return f'{self.final_decisions} ({self.final_score})'


