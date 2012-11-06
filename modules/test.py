import build, ivy
from py2neo import neo4j, cypher, gremlin
from sets import ImmutableSet
from collections import defaultdict

INCOMING = neo4j.Direction.INCOMING
OUTGOING = neo4j.Direction.OUTGOING

try:
    G = neo4j.GraphDatabaseService('http://localhost:7474/db/data')
    refnode = G.get_reference_node()
    ncbi_node_idx = G.get_or_create_index(
        neo4j.Node, 'ncbi_node', config={'type':'exact'})
    ncbi_name_idx = G.get_or_create_index(
        neo4j.Node, 'ncbi_name', config={'type':'exact'})
    ## stree_idx = G.get_or_create_index(
    ##     neo4j.Node, 'stree', config={'type':'exact'})
    ## stree_ref = refnode.get_single_related_node(OUTGOING, 'STREE_REF')
    ## if not stree_ref:
    ##     stree_ref = G.create({}, (refnode, 'STREE_REF', 0))[0]
except Exception as e:
    print 'neo4j server not found:', e

def bulbs_connect(uri='http://localhost:7474/db/data'):
    from bulbs.neo4jserver import Graph
    from bulbs.config import Config
    config = Config(uri)
    config.autoindex = False
    G = Graph(config)
    return G

gid2name = {}
def getname(gid):
    s = gid2name.get(gid)
    if s: return s
    n = G.get_node(gid)
    s = filter(lambda x:x['name_class']=='scientific name',
               n.get_related_nodes(INCOMING, 'NAME_OF'))[0]['name']
    
    s = s.replace(' ', '_')
    gid2name[gid] = s
    return s
    
rec = db.stree(3)
root = build.stree(db, rec.id)

for n in root.leaves():
    node = None
    if n.rec.ottol_name:
        ottol_name = db.ottol_name(n.rec.ottol_name)
        if ottol_name.ncbi_taxid:
            taxid = ottol_name.ncbi_taxid
            node = ncbi_node_idx.get('taxid', str(taxid))[0]
        else:
            name = n.rec.ottol_name.name
            v = ncbi_name_idx.get('name', name)
            if len(v)==1:
                node = v[0].get_single_related_node(OUTGOING, 'NAME_OF')
            elif len(v)>1:
                print len(v), 'synonyms of ottol_name', name
            else: print 'ottol_name', name, 'not found'
    else:
        name = n.rec.label
        v = ncbi_name_idx.get('name', name)
        if len(v)==1:
            node = v[0].get_single_related_node(OUTGOING, 'NAME_OF')
        elif len(v)>1:
            print len(v), 'synonyms of label', name
        else: print 'label', name, 'not found'
    n.ncbi_node = node
    n.label = getname(n.ncbi_node.id)

for n in root.postiter():
    if n.isleaf:
        n.leaf_gids = ImmutableSet([n.ncbi_node.id])
    else:
        if len(n.children)==1: n.leaf_gids = n.children[0].leaf_gids
        else: n.leaf_gids = reduce(
            lambda a,b:a|b, [ x.leaf_gids for x in n.children ])

nodes = [ n.ncbi_node for n in root.leaves() ]

## life = ncbi_node_idx.get('taxid','1')[0]
## q = ('start leaf=node({leaf}) '
##      'match p = leaf-[r:CHILD_OF*]->anc<-[:NAME_OF]-name '
##      ## 'where (name.name_class = "scientific name") '
##      'return leaf, r')
## rows, meta = cypher.execute(G, q, params={
##     'root': life.id,
##     'leaf': [ x.id for x in nodes ]})

q = """
leaves = %s
v = []
leaves.each() {
    leaf -> v.add([leaf]+g.v(leaf).out('CHILD_OF').loop(1){true}{true}*.id)
}
v
""" % [ x.id for x in nodes ]
resp = bulbs_connect().gremlin.execute(q).content
assert len(resp)==len(nodes)
groot = build.Node(isroot=True)
v = set([ x[-1] for x in resp ])
while len(v)==1:
    groot.gid = list(v)[0]
    groot.label = getname(groot.gid)
    for x in resp: x.pop()
    v = set([ x[-1] for x in resp ])
gleaves = {groot: resp}
def update(gleaves):
    for gnode, rows in gleaves.items():
        v = set([ x[-1] for x in rows if x ])
        for gid in v:
            child = build.Node(gid=gid, label=getname(gid))
            gnode.add_child(child)
            crows = [ r for r in rows if r and r[-1]==gid ]
            for r in crows: r.pop()
            if not any(crows): child.isleaf=True
            gleaves[child] = crows
        del gleaves[gnode]
while any(resp): update(gleaves)

for i, n in enumerate(groot): n.id = i

leafgids = defaultdict(list)
for n in groot.postiter():
    n.ncbi_node = G.get_node(n.gid)
    if n.isleaf:
        n.leaf_gids = ImmutableSet([n.gid])
    else:
        if len(n.children)==1: n.leaf_gids = n.children[0].leaf_gids
        else: n.leaf_gids = reduce(
            lambda a,b:a|b, [ x.leaf_gids for x in n.children ])
    leafgids[n.leaf_gids].append(n)
    ## print n.label, n.leaf_gids, leafgids[n.leaf_gids]

nodes = list(root.postiter())
for n in nodes:
    v = leafgids.get(n.leaf_gids)
    if v:
        gnode = v[0]
        n.gid = gnode.gid
        n.label = getname(n.gid)
        ref = n
        for gnode in v[1:]:
            newnode = build.Node(gid=gnode.gid, label=getname(gnode.gid),
                                 leaf_gids=ref.leaf_gids)
            p = ref.prune()
            newnode.add_child(ref)
            p.add_child(newnode)
            ref = newnode
    else:
        #print 'no leafgids for', n, map(getname, sorted(n.leaf_gids))
        pass