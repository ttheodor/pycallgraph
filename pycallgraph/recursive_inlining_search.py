from collections import defaultdict


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
    assert cg.number_edges() > 0
    if cg.number_edges() == 1:
        e = cg.edges()[0]
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

    yield from generate_configurations_recursive(
        cg_e_dropped, decisions + [InliningDecision(e, False)])
    yield from generate_configurations_recursive(
        cg_e_merged, decisions + [InliningDecision(e, True)])


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
            icc_tag += 1
            for cc_alternative in icc:
                yield from generate_candidates_from_config(
                    cc_alternative, decisions + [('icc_tag', icc_tag)])
        return

    if isinstance(conf[-1], tuple):
        decisions = decisions + conf[:-1]
        yield from generate_candidates_from_config(conf[-1], decisions)
    else:
        yield decisions + conf


class ComponentDecisions:
    def __init__(self):
        self.decisions = []
        self.component_tags = []
        self.component_decisions = defaultdict(set)

    def __str__(self):
        return f'decisions: {self.decisions}\ncomonent tags: {self.component_tags}\ncomponent_decisions: {self.component_decisions}'

    def add_component_tag(self, i):
        self.component_tags.append(i)

    def add_decision(self, d):
        self.decisions.append(d)
        for t in self.component_tags:
            self.component_decisions[t].add(d)


def convert_candidate_to_component_decisions(cand):
    cds = ComponentDecisions()
    for e in cand:
        if isinstance(e, tuple):
            assert e[0] == 'icc_tag'
            cds.add_component_tag(e[1])
        else:
            cds.add_decision(e)
    return cds
