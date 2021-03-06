import plugin_treeViewer as util
from ivy_local.tree import *
import datetime, sys, math, copy
import build as build


def revertEdit( db, session, tree, editInfo ):

    getattr( sys.modules[__name__], ''.join( [ 'revert', editInfo.action.capitalize() ] ) )( db, session, tree, editInfo )

   
def revertPrune( db, session, tree, editInfo ):

    prunedClade = \
        getattr( build, ''.join( [ editInfo.originalTreeType, 'Clade' ] ) )\
            ( db, editInfo.affected_node_id, Storage(), Storage( pruned = True, editId = editInfo.id ) )

    parentNode = util.getNodeById( tree, editInfo.affected_clade_id )

    parentNode.add_child( prunedClade );


def revertReplace( db, session, tree, editInfo ):

    replacedClade = \
        getattr( build, ''.join( [ editInfo.originalTreeType, 'Clade' ] ) )\
            ( db, editInfo.affected_node_id, Storage(), Storage( pruned = True, editId = editInfo.id ) )

    replacingClade = util.getNodeById( tree, editInfo.target_gnode )

    parentNode = replacingClade.parent

    parentNode.remove_child( replacingClade )
    parentNode.add_child( replacedClade )


def revertGraft( db, session, tree, editInfo ):

    graftedClade = util.getNodeById( tree, editInfo.target_gnode )

    parentNode = graftedClade.parent
    parentNode.remove_child( graftedClade )


def graftClade( tree, graftingOntoNodeId, graftingClade ):

    parent = util.getNodeById( tree, graftingOntoNodeId )
    parent.add_child( graftingClade )
    
    graftingClade.meta[ 'targetGNode' ] = True
    parent.meta[ 'affectedCladeId' ] = True


def postGraftDBUpdate( db, session, request, auth, tree, graftingOntoNodeId, graftingClade ):
    
    treeType = session.TreeViewer.treeType

    if treeType == 'source':

        ( columnRootNodeIds, collapsedNodeIds ) = gatherTreeStateIds( session )
        session.TreeViewer.recentlyEditedSourceTreeId = session.TreeViewer.treeId

        session.TreeViewer.treeId = createGTreeRecord( db, auth, request.vars.treeName, request.vars.treeDescription )
        
        index( tree )
        
        reference = dict( newCladeId = graftingClade.id,
                          targetGNode = None,
                          oldAffectedCladeId = graftingOntoNodeId,
                          newAffectedCladeId = None,
                          columnRootNodeIds = columnRootNodeIds,
                          collapsedNodeIds = collapsedNodeIds )
        
        insertSnodesToGtree( db, session.TreeViewer.treeId, tree, None, reference )
        
        createEditRecord( db,
                          auth,
                          session.TreeViewer.treeId,
                          'graft',
                          reference['newAffectedCladeId'],
                          None,
                          graftingClade.id,
                          request.vars.replacingCladeTreeType,
                          request.vars.comment,
                          treeType,
                          auth.user.id,
                          reference['targetGNode'] )

        updateSessionForGraftedSourceTree( session, columnRootNodeIds, collapsedNodeIds, graftingClade )

    else:

        index( tree )
        
        updatedNextBackValues = getCollapsedNodeIds( session )

        updateGtreeDB( db, tree, updatedNextBackValues )
        
        reference = dict( newCladeId = graftingClade.id, targetGNode = None )
        
        insertGNodesToGtree( db, session.TreeViewer.treeId, graftingClade, graftingOntoNodeId, request.vars.graftingNodeTreeType, reference )
        
        editId = createEditRecord( db,
                                   auth,
                                   session.TreeViewer.treeId,
                                   'graft',
                                   graftingOntoNodeId,
                                   None,
                                   graftingClade.id,
                                   request.vars.replacingCladeTreeType,
                                   request.vars.comment,
                                   treeType,
                                   auth.user.id,
                                   reference['targetGNode'] )
    
        updateSessionForGraftedGraftedTree( session, updatedNextBackValues, graftingClade )



def replaceClade( tree, replacedNodeId, replacingClade ):

    cladeToReplace = util.getNodeById( tree, replacedNodeId )
    parentOfReplaced = cladeToReplace.parent

    parentOfReplaced.remove_child( cladeToReplace )
    parentOfReplaced.add_child( replacingClade )

    parentOfReplaced.meta[ 'affectedCladeId' ] = True
    replacingClade.meta[ 'targetGNode' ] = True


def postReplaceDBUpdate( db, session, request, auth, tree, replacedCladeRow, replacingClade ):    
  
    treeType = session.TreeViewer.treeType

    replacingCladeId = int( request.vars.replacingNodeId )

    if treeType == 'source':

        ( columnRootNodeIds, collapsedNodeIds ) = gatherTreeStateIds( session )
        session.TreeViewer.recentlyEditedSourceTreeId = session.TreeViewer.treeId

        session.TreeViewer.treeId = createGTreeRecord( db, auth, request.vars.treeName, request.vars.treeDescription )
        
        index( tree )
        
        reference = dict( newCladeId = replacingCladeId,
                          targetGNode = None,
                          oldAffectedCladeId = replacedCladeRow.parent,
                          newAffectedCladeId = None,
                          columnRootNodeIds = columnRootNodeIds,
                          collapsedNodeIds = collapsedNodeIds )
        
        insertSnodesToGtree( db, session.TreeViewer.treeId, tree, None, reference )
        
        createEditRecord( db,
                          auth,
                          session.TreeViewer.treeId,
                          'replace',
                          reference['newAffectedCladeId'],
                          replacedCladeRow.id,
                          replacingCladeId,
                          request.vars.replacingCladeTreeType,
                          request.vars.comment,
                          treeType,
                          auth.user.id,
                          reference['targetGNode'] )

        updateSessionForReplacedSourceTree( session, columnRootNodeIds, collapsedNodeIds, replacedCladeRow, reference['targetGNode'] )

    else:
        
        editId = createEditRecord( db,
                                   auth,
                                   session.TreeViewer.treeId,
                                   'replace',
                                   replacedCladeRow.parent,
                                   replacedCladeRow.id,
                                   replacingCladeId,
                                   request.vars.replacingCladeTreeType,
                                   request.vars.comment,
                                   treeType,
                                   auth.user.id,
                                   None )
    
        pruneGNodeRecords( db, session.TreeViewer.treeId, replacedCladeRow, editId )

        index( tree )
        
        updatedNextBackValues = getCollapsedNodeIds( session )

        updateGtreeDB( db, tree, updatedNextBackValues )
        
        reference = dict( newCladeId = replacingClade.id, targetGNode = None )
        
        insertGNodesToGtree( db, session.TreeViewer.treeId, replacingClade, replacedCladeRow.parent, request.vars.replacingNodeTreeType, reference )

        db( db.gtree_edit.id == editId ).update( target_gnode = reference['targetGNode'] )

        updateSessionForReplacedGraftedTree( session, updatedNextBackValues, replacedCladeRow )


def updateSessionForGraftedSourceTree( session, columnRootNodeIds, collapsedNodeIds, graftingClade ):

    session.TreeViewer.treeType = 'grafted'
    session.TreeViewer.strNodeTable = 'gnode'

    session.TreeViewer.treeConfig[ session.TreeViewer.treeType ][ session.TreeViewer.treeId ] = \
        session.TreeViewer.treeConfig[ 'source' ][ session.TreeViewer.recentlyEditedSourceTreeId ]

    oldTreeState = session.TreeViewer.treeState[ 'source' ][ session.TreeViewer.recentlyEditedSourceTreeId ]
    newTreeState = session.TreeViewer.treeState[ session.TreeViewer.treeType ][ session.TreeViewer.treeId ] = \
                   Storage( columns = [ ], formerlyCollapsedNodeStorage = Storage() )


    for column in oldTreeState.columns:

        rootNodeId = columnRootNodeIds[ column.rootNodeId ]

        newCollapsedNodeStorage = Storage()

        for ( collapsedNodeId, collapsedNodeData ) in column.collapsedNodeStorage.items():
           
            #if collapsedNodeIds[ collapsedNodeId ] is None: break
            if collapsedNodeIds[ collapsedNodeId ] is None: continue

            newCollapsedNodeStorage[ collapsedNodeIds[ collapsedNodeId ].nodeId ] = copy.copy( collapsedNodeData )
            newCollapsedNodeStorage[ collapsedNodeIds[ collapsedNodeId ].nodeId ]['next'] = collapsedNodeIds[ collapsedNodeId ]['next']
            newCollapsedNodeStorage[ collapsedNodeIds[ collapsedNodeId ].nodeId ]['back'] = collapsedNodeIds[ collapsedNodeId ]['back']

        newTreeState.columns.append( Storage( rootNodeId = rootNodeId, collapsedNodeStorage = newCollapsedNodeStorage, keepVisibleNodeStorage = Storage() ) )

    newTreeState.totalNodes = \
        oldTreeState.totalNodes + 1 + \
        math.floor( ( graftingClade.back - graftingClade.next - 1 ) / 2 )

    newTreeState.allNodesHaveLength = oldTreeState.allNodesHaveLength

    del session.TreeViewer.recentlyEditedSourceTreeId


def updateSessionForReplacedSourceTree( session, columnRootNodeIds, collapsedNodeIds, replacedCladeRow, replacingClade ):

    session.TreeViewer.treeType = 'grafted'
    session.TreeViewer.strNodeTable = 'gnode'

    session.TreeViewer.treeConfig[ session.TreeViewer.treeType ][ session.TreeViewer.treeId ] = \
        session.TreeViewer.treeConfig[ 'source' ][ session.TreeViewer.recentlyEditedSourceTreeId ]

    oldTreeState = session.TreeViewer.treeState[ 'source' ][ session.TreeViewer.recentlyEditedSourceTreeId ]
    newTreeState = session.TreeViewer.treeState[ session.TreeViewer.treeType ][ session.TreeViewer.treeId ] = \
                   Storage( columns = [ ], formerlyCollapsedNodeStorage = Storage() )


    for column in oldTreeState.columns:

        if columnRootNodeIds[ column.rootNodeId ] is None: break
            
        rootNodeId = columnRootNodeIds[ column.rootNodeId ]

        newCollapsedNodeStorage = Storage()

        for ( collapsedNodeId, collapsedNodeData ) in column.collapsedNodeStorage.items():
           
            #if collapsedNodeIds[ collapsedNodeId ] is None: break
            if collapsedNodeIds[ collapsedNodeId ] is None: continue

            newCollapsedNodeStorage[ collapsedNodeIds[ collapsedNodeId ].nodeId ] = copy.copy( collapsedNodeData )
            newCollapsedNodeStorage[ collapsedNodeIds[ collapsedNodeId ].nodeId ]['next'] = collapsedNodeIds[ collapsedNodeId ]['next']
            newCollapsedNodeStorage[ collapsedNodeIds[ collapsedNodeId ].nodeId ]['back'] = collapsedNodeIds[ collapsedNodeId ]['back']

        newTreeState.columns.append( Storage( rootNodeId = rootNodeId, collapsedNodeStorage = newCollapsedNodeStorage, keepVisibleNodeStorage = Storage() ) )

    newTreeState.totalNodes = \
        oldTreeState.totalNodes - \
        math.floor( ( replacedCladeRow.back - replacedCladeRow.next - 1 ) / 2 ) + \
        math.floor( ( replacingClade.back - replacingClade.next - 1 ) / 2 )

    newTreeState.allNodesHaveLength = oldTreeState.allNodesHaveLength

    del session.TreeViewer.recentlyEditedSourceTreeId



def updateSessionForPrunedSourceTree( session, columnRootNodeIds, collapsedNodeIds, prunedNodeRow ):

    session.TreeViewer.treeType = 'grafted'
    session.TreeViewer.strNodeTable = 'gnode'

    session.TreeViewer.treeConfig[ session.TreeViewer.treeType ][ session.TreeViewer.treeId ] = \
        session.TreeViewer.treeConfig[ 'source' ][ session.TreeViewer.recentlyEditedSourceTreeId ]

    oldTreeState = session.TreeViewer.treeState[ 'source' ][ session.TreeViewer.recentlyEditedSourceTreeId ]
    newTreeState = session.TreeViewer.treeState[ session.TreeViewer.treeType ][ session.TreeViewer.treeId ] = \
                   Storage( columns = [ ], formerlyCollapsedNodeStorage = Storage() )
       
    for column in oldTreeState.columns:

        #if columnRootNodeIds[ column.rootNodeId ] is None: break
            
        rootNodeId = columnRootNodeIds[ column.rootNodeId ]

        newCollapsedNodeStorage = Storage()

        for ( collapsedNodeId, collapsedNodeData ) in column.collapsedNodeStorage.items():
           
            #if collapsedNodeIds[ collapsedNodeId ] is None: break
            if collapsedNodeIds[ collapsedNodeId ] is None: continue

            newCollapsedNodeStorage[ collapsedNodeIds[ collapsedNodeId ].nodeId ] = copy.copy( collapsedNodeData )
            newCollapsedNodeStorage[ collapsedNodeIds[ collapsedNodeId ].nodeId ]['next'] = collapsedNodeIds[ collapsedNodeId ]['next']
            newCollapsedNodeStorage[ collapsedNodeIds[ collapsedNodeId ].nodeId ]['back'] = collapsedNodeIds[ collapsedNodeId ]['back']

        newTreeState.columns.append( Storage( rootNodeId = rootNodeId, collapsedNodeStorage = newCollapsedNodeStorage, keepVisibleNodeStorage = Storage() ) )

    newTreeState.totalNodes = oldTreeState.totalNodes - math.floor( ( prunedNodeRow.back - prunedNodeRow.next - 1 ) / 2 )
    newTreeState.allNodesHaveLength = oldTreeState.allNodesHaveLength

    del session.TreeViewer.recentlyEditedSourceTreeId
    

def pruneClade( tree, nodeId ):
    
    cladeToPrune = util.getNodeById( tree, nodeId )
    parentClade = cladeToPrune.parent

    parentClade.remove_child( cladeToPrune )

    parentClade.meta[ 'affectedCladeId' ] = True


def postPruneDBUpdate( db, session, request, auth, tree, prunedNodeRow ):

    treeType = session.TreeViewer.treeType

    if treeType == 'source':

        ( columnRootNodeIds, collapsedNodeIds ) = gatherTreeStateIds( session )
        session.TreeViewer.recentlyEditedSourceTreeId = session.TreeViewer.treeId

        session.TreeViewer.treeId = createGTreeRecord( db, auth, request.vars.treeName, request.vars.treeDescription )

        index( tree )

        reference = dict( \
            oldAffectedCladeId = int( prunedNodeRow.parent ),
            newAffectedCladeId = None,
            columnRootNodeIds = columnRootNodeIds,
            collapsedNodeIds = collapsedNodeIds )

        insertSnodesToGtree( db, session.TreeViewer.treeId, tree, None, reference )
        
        createEditRecord( db,
                          auth,
                          session.TreeViewer.treeId,
                          'prune',
                          reference['newAffectedCladeId'],
                          prunedNodeRow.id,
                          None,
                          None,
                          request.vars.comment,
                          treeType,
                          auth.user.id )

        updateSessionForPrunedSourceTree( session, columnRootNodeIds, collapsedNodeIds, prunedNodeRow )

    else:
 

        editId = createEditRecord( db,
                                   auth,
                                   session.TreeViewer.treeId,
                                   'prune',
                                   prunedNodeRow.parent,
                                   prunedNodeRow.id,
                                   None,
                                   None,
                                   request.vars.comment,
                                   treeType,
                                   auth.user.id )       

        pruneGNodeRecords( db, session.TreeViewer.treeId, prunedNodeRow, editId )

        index( tree )

        updatedNextBackValues = getCollapsedNodeIds( session )

        updateGtreeDB( db, tree, updatedNextBackValues )
        
        updateSessionForPrunedGraftedTree( session, updatedNextBackValues, prunedNodeRow )


def getCollapsedNodeIds( session ):
   
    collapsedNodeStorage = Storage()

    treeState = session.TreeViewer.treeState[ session.TreeViewer.treeType ][ session.TreeViewer.treeId ]

    for column in treeState.columns:
        
        for ( collapsedNodeId, collapsedNodeData ) in column.collapsedNodeStorage.items():

            collapsedNodeStorage[ collapsedNodeId ] = Storage()
    
    return collapsedNodeStorage


def updateSessionForGraftedGraftedTree( session, updatedNextBackValues, graftingClade ):

    treeState = session.TreeViewer.treeState[ session.TreeViewer.treeType ][ session.TreeViewer.treeId ]

    for index in range( len( treeState.columns ) ):
    
        column = treeState.columns[ index ]

        for ( collapsedNodeId, collapsedNodeData ) in column.collapsedNodeStorage.items():

            collapsedNodeData[ 'next' ] = updatedNextBackValues[ collapsedNodeId ].next
            collapsedNodeData[ 'back' ] = updatedNextBackValues[ collapsedNodeId ].back


def updateSessionForReplacedGraftedTree( session, updatedNextBackValues, replacedCladeRow ):

    treeState = session.TreeViewer.treeState[ session.TreeViewer.treeType ][ session.TreeViewer.treeId ]

    leaveLoop = False

    for index in range( len( treeState.columns ) ):
    
        if leaveLoop: break

        column = treeState.columns[ index ]

        for ( collapsedNodeId, collapsedNodeData ) in column.collapsedNodeStorage.items():

            if( ( collapsedNodeId == replacedCladeRow.id ) or
                ( util.isDescendant( collapsedNodeData, replacedCladeRow ) ) ):

                del column.collapsedNodeStorage[ collapsedNodeId ]

                if( ( index < ( len( treeState.columns ) - 1 ) ) and
                    ( collapsedNodeId == treeState.columns[ index + 1 ].rootNodeId ) ):

                    while( ( len( treeState.columns ) - 1 ) > index ):
                        treeState.columns.pop()

                    leaveLoop = True

            else:
                
                collapsedNodeData[ 'next' ] = updatedNextBackValues[ collapsedNodeId ].next
                collapsedNodeData[ 'back' ] = updatedNextBackValues[ collapsedNodeId ].back





def updateSessionForPrunedGraftedTree( session, updatedNextBackValues, prunedNodeRow ):

    treeState = session.TreeViewer.treeState[ session.TreeViewer.treeType ][ session.TreeViewer.treeId ]

    leaveLoop = False

    for index in range( len( treeState.columns ) ):
    
        if leaveLoop: break

        column = treeState.columns[ index ]

        for ( collapsedNodeId, collapsedNodeData ) in column.collapsedNodeStorage.items():

            if( ( collapsedNodeId == prunedNodeRow.id ) or
                ( util.isDescendant( collapsedNodeData, prunedNodeRow ) ) ):

                del column.collapsedNodeStorage[ collapsedNodeId ]

                if( ( index < ( len( treeState.columns ) - 1 ) ) and
                    ( collapsedNodeId == treeState.columns[ index + 1 ].rootNodeId ) ):

                    while( ( len( treeState.columns ) - 1 ) > index ):
                        treeState.columns.pop()

                    leaveLoop = True

            else:
                
                collapsedNodeData[ 'next' ] = updatedNextBackValues[ collapsedNodeId ].next
                collapsedNodeData[ 'back' ] = updatedNextBackValues[ collapsedNodeId ].back


def gatherTreeStateIds( session ):

    columnRootNodeIds = Storage()
    collapsedNodeIds = Storage()

    for column in session.TreeViewer.treeState[ session.TreeViewer.treeType ][ session.TreeViewer.treeId ].columns:

        columnRootNodeIds[ column.rootNodeId ] = None

        for ( collapsedNodeId, collapsedNodeData ) in column.collapsedNodeStorage.items():
            
            collapsedNodeIds[ collapsedNodeId ] = None

    return ( columnRootNodeIds, collapsedNodeIds )


def updateGtreeDB( db, currentNode, updatedNextBackValues ):

    db( db.gnode.id == currentNode.id ).update( \
        next = currentNode.next,
        back = currentNode.back )

    for child in currentNode.children:
        updateGtreeDB( db, child, updatedNextBackValues )

    if( currentNode.id in updatedNextBackValues ):

        updatedNextBackValues[ currentNode.id ] = Storage( next = currentNode.next, back = currentNode.back )


def insertGNodesToGtree( db, gtreeId, node, parentId, nodeType, reference ):

    snode = db( db.gnode.id == node.id ).select()[0].snode if nodeType == 'grafted' else node.id

    gnode = db.gnode.insert( \
        label = node.label,
        isleaf = node.isleaf,
        ntips = node.descendantTipCount,
        parent = parentId,
        next = node.next,
        back = node.back,
        length = node.length,
        tree = gtreeId,
        snode = snode,
        pruned = False )

    if( node.id == reference['newCladeId'] ):
        reference['targetGNode'] = gnode

    for child in node.children:
        insertGNodesToGtree( db, gtreeId, child, gnode, nodeType, reference )



def insertSnodesToGtree( db, gtreeId, node, parentId, reference=None ):
    
    gnode = db.gnode.insert( \
        label = node.label,
        isleaf = node.isleaf,
        ntips = node.descendantTipCount,
        parent = parentId,
        next = node.next,
        back = node.back,
        length = node.length,
        tree = gtreeId,
        snode = node.id,
        pruned = False )

    if( reference is not None ):
        
        if( ( 'newCladeId' in reference ) and ( node.id == reference['newCladeId'] ) and ( 'targetGNode' in node.meta ) ):
            
            reference['targetGNode'] = gnode
        
        if( ( 'oldAffectedCladeId' in reference ) and ( node.id == reference['oldAffectedCladeId'] ) and ( 'affectedCladeId' in node.meta ) ):

            reference['newAffectedCladeId'] = gnode
        
        if( ( 'columnRootNodeIds' in reference ) and ( node.id in reference[ 'columnRootNodeIds' ] ) ):
            reference[ 'columnRootNodeIds' ][ node.id ] = gnode
        
        if( ( 'collapsedNodeIds' in reference ) and ( node.id in reference[ 'collapsedNodeIds' ] ) ):
            reference[ 'collapsedNodeIds' ][ node.id ] = Storage( nodeId = gnode, next = node.next, back = node.back )
    
    node.id = gnode

    for child in node.children:
        insertSnodesToGtree( db, gtreeId, child, gnode, reference )


def createGTreeRecord( db, auth, name, desc ):

    #The contributor field is probably better as a user id.  I joined the first and last names in an attempt to normalize users logging in with multiple email addresses.
    return db.gtree.insert(
        contributor = ' '.join( [ auth.user.first_name, auth.user.last_name ] ),
        title = name,
        comment = desc,
        date = datetime.datetime.now() ).id


def createEditRecord( db, auth, treeId, action, affectedCladeId, affectedNodeId, newNodeOriginId, newNodeOriginType, comment, originalTreeType, userId, targetGnode = None ):

    insertDict = dict(
        gtree = treeId,
        action = action,
        affected_clade_id = affectedCladeId,
        affected_node_id = affectedNodeId,
        comment = comment,
        originalTreeType = originalTreeType,
        user = userId )

    if action != 'prune':
        insertDict['newNodeOriginId'] = newNodeOriginId
        insertDict['newNodeOriginType'] = newNodeOriginType
        insertDict['target_gnode'] = targetGnode

    return db.gtree_edit.insert( **insertDict ).id


def pruneGNodeRecords( db, treeId, node, editId ):

    nodesToPrune = db(
        ( db.gnode.tree == treeId ) & 
        ( db.gnode.pruned == False ) & 
        ( db.gnode.next >= node.next ) &
        ( db.gnode.back <= node.back ) ).select( db.gnode.id )

    for nodeToPrune in nodesToPrune:
        db.prune_detail.insert( pruned_gnode = nodeToPrune.id, gtree_edit = editId )
    
    db( ( db.gnode.tree == treeId ) & 
        ( db.gnode.pruned == False ) & 
        ( db.gnode.next >= node.next ) &
        ( db.gnode.back <= node.back ) ).update( pruned = True )
