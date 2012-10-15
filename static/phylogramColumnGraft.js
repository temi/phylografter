BioSync.TreeGrafter.RenderUtil.Column = function( renderObj ) {

    this.renderObj = renderObj;
    this.make = renderObj.make;
    return this;
}

BioSync.TreeGrafter.RenderUtil.Column.prototype = new BioSync.TreeViewer.RenderUtil.Column();
BioSync.TreeGrafter.RenderUtil.Column.constructor = BioSync.TreeGrafter.RenderUtil.Column;
BioSync.TreeGrafter.RenderUtil.Column.prototype.super = BioSync.TreeViewer.RenderUtil.Column.prototype;

BioSync.TreeGrafter.RenderUtil.Column.prototype.handlePruneCladeOptionClick = function() {

    this.nodeIdToPrune = this.closestNodeToMouse.id;

    this.renderObj.pruneClade( { column: this, nodeId: this.nodeIdToPrune } );
}