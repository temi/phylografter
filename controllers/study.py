import os, uuid
from cStringIO import StringIO
from gluon.custom_import import track_changes
from gluon.storage import Storage
from gluon.tools import Crud

from StringIO import StringIO
import requests
import json
import time
import nexson
import tempfile
import gzip
from link import doi2url, normalize_doi_for_url

from externalproc import get_external_proc_dir_for_upload, invoc_status, \
    ExternalProcStatus, get_logger, get_conf, do_ext_proc_launch

track_changes()
#import ivy
#treebase = ivy.treebase
from ivy_local import treebase
response.subtitle = A("Studies", _href=URL('study','index'))

class Virtual(object):
    def study_url(self):
        u = URL(c="study",f="view",args=[self.study.id],extension="")
        s = self.study.citation.decode('utf8')
        N = 50
        short = s
        if len(s)>N: short = s[:N-3]+" ..."
        return A(short, _href=u, _title=s)

    def trees(self):
        rows = db(db.stree.study==self.study.id).select()
        ul = DIV()
        for r in rows:
            a = A(r.type, _href=URL('stree','svgView',args=r.id,extension=''))
            ul.append(DIV(a))
        return ul.xml()

## def index():
##     t = db.study

##     class Virtual(object):
##         @virtualsettings(label='Citation')
##         def study_url(self):
##             study = t[self.study.id]
##             u = URL(c="study",f="view",args=[study.id])
##             s = study.citation
##             N = 50
##             if len(s)>N: s = s[:N-3]+" ..."
##             return A(s, _href=u, _title=study.citation)

##         @virtualsettings(label='OTUs')
##         def otus(self):
##             study = t[self.study.id]
##             n = db(db.otu.study==study.id).count()
##             if n > 0:
##                 u = URL(c="otu",f="study",args=[study.id])
##                 return A(str(n), _href=u)
##             else:
##                 return str(n)

##     powerTable = plugins.powerTable
##     powerTable.datasource = t
##     powerTable.dtfeatures["sScrollY"] = "100%"
##     powerTable.dtfeatures["sScrollX"] = "100%"
##     powerTable.virtualfields = Virtual()
##     powerTable.headers = "labels"
##     powerTable.showkeycolumn = False
##     powerTable.dtfeatures["bJQueryUI"] = request.vars.get("jqueryui",True)
##     ## powerTable.uitheme = request.vars.get("theme","cupertino")
##     powerTable.uitheme = request.vars.get("theme","smoothness")
##     powerTable.dtfeatures["bStateSave"] = 'true'
##     powerTable.dtfeatures["iDisplayLength"] = 25
##     powerTable.dtfeatures["aaSorting"] = [[6,'desc']]
##     powerTable.dtfeatures["sPaginationType"] = request.vars.get(
##         "pager","full_numbers"
##         ) # two_button scrolling
##     powerTable.columns = ["study.id",
##                           "study.focal_clade",
##                           "virtual.study_url",
##                           "study.year_published",
##                           "virtual.otus",
##                           ## "study.treebase_id",
##                           ## "study.contributor",
##                           "study.uploaded"]
##     #powerTable.hiddencolumns = ["study.treebase_id"]
##     details = dict(detailscallback=URL(c="study",f="details"))
##     powerTable.extra = dict(autoresize=True,
##                             ## tooltip={},
##                             details=details)
##     return dict(table=powerTable.create())

def index():
    theme = "smoothness"
    for x in (
        # 'DataTables-1.8.1/media/js/jquery.js',  # there's already a newer (Bootstrap-compatible) jQuery loaded!
        'DataTables-1.8.1/media/js/jquery.dataTables.min.js',
        'DataTables-1.8.1/media/css/bootstrap_table.css',
        'DataTables-1.8.1/media/ui/css/%s/jquery-ui-1.8.5.custom.css' % theme):
        response.files.append(URL('static',x))

    t = db.study
    colnames = ["Id", "Focal clade", "Citation",
                "Year", "OTUs", "Trees", "Uploaded", "By"]
    widths = ["5%", "10%", "25%", "5%", "5%", "15%","10%","7%"]
    tid = "studies"
    table = TABLE(_id=tid, _class="display")
    table.append(THEAD(TR(*[ TH(f, _width=w)
                             for f, w in zip(colnames, widths) ])))
    table.append(TBODY(TR(TD("Loading data from server",
                             _colspan=len(colnames),
                             _class="dataTables_empty"))))
    table.append(TFOOT(TR(
        TH(INPUT(_name="search_id",
                 _style="width:100%",_class="search_init",
                 _title="search Id" )),
        TH(INPUT(_name="search_focal_clade",
                 _style="width:100%",_class="search_init",
                 _title="search focal clade" )),
        TH(INPUT(_name="search_citation",
                 _style="width:100%",_class="search_init",
                 _title="search citation" )),
        TH(INPUT(_name="search_year",
                 _style="width:100%",_class="search_init",
                 _title="search publication year" )),
        TH(),
        TH(),
        TH(INPUT(_name="search_uploaded",
                 _style="width:100%",_class="search_init",
                 _title="search uploaded" )),
        TH(INPUT(_name="search_person",
                 _style="width:100%",_class="search_init",
                 _title="search person" )),
        )))

    return dict(tid=tid, table=table)
    
def dtrecords():
    ## for k, v in sorted(request.vars.items()):
    ##     print k, ":", v

    t = db.study
    t.virtualfields.append(Virtual())
    otu_count = db.otu.id.count()
    left = db.otu.on(db.otu.study==db.study.id)

    fields = [ t.id, t.focal_clade_ott, t.citation, t.year_published,
               otu_count, None, t.uploaded, t.contributor ]
    orderby = []
    if request.vars.iSortCol_0:
        for i in range(int(request.vars.iSortingCols or 1)):
            col = int(request.vars.get("iSortCol_%s" % i))
            if col != 5:
                scol = fields[col]
                sdir = request.vars.get("sSortDir_%s" % i) or "asc"
                if sdir == "desc": scol = ~scol
                orderby.append(scol)

    start = int(request.vars.iDisplayStart or 0)
    end = start + int(request.vars.iDisplayLength or 10)
    limitby = (start,end)
    q = q0 = (t.id>0)
    
    for i, f in enumerate(
        [ t.id, t.focal_clade_ott, t.citation,
          t.year_published, t.uploaded, t.contributor ]):
        sterm = request.vars.get("sSearch_%s" % i)
        if sterm:
            if f is t.focal_clade_ott:
                q &= ((t.focal_clade_ott==db.ott_node.id)&
                      (db.ott_node.name.like('%'+sterm+'%')))
            else:
                q &= f.like('%'+sterm+'%')
                
    rows = db(q).select(*filter(None,fields), groupby=t.id, left=left,
                        orderby=orderby, limitby=limitby)

    def otus(rec):
        n = rec[otu_count]
        if n > 0:
            u = URL(c="otu",f="study",args=[rec.study.id],extension='')
            return A(str(n), _href=u).xml()
        else:
            return str(n)

    data = [ (r.study.id,
              (r.study.focal_clade_ott.name if r.study.focal_clade_ott else ''),
              r.study.study_url.xml(),
              r.study.year_published,
              otus(r),
              r.study.trees,
              r.study.uploaded,
              r.study.contributor)
             for r in rows ]

    totalrecs = db(q0).count()
    disprecs = db(q).count()
    return dict(aaData=data,
                iTotalRecords=totalrecs,
                iTotalDisplayRecords=disprecs,
                sEcho=int(request.vars.sEcho))

def details():
    t = db.study
    study = None
    for k in request.vars.keys():
        if k[:3] == 'dt_':
            study = int(request.vars[k].split(".")[-1])
            break

    tbl = TABLE(TR(TD("Nothing to see here")))

    if study:
        stree = db.stree
        comment = t[study].comment
        edit = A("Edit record", _href=URL(c="study",f="view",args=[study]))
        newtree = A("add new tree",
                    _href=URL(c="stree",f="create",args=[study]))
        newfile = A("add data file",
                    _href=URL(c="study",f="addfile",args=[study]))
        span = SPAN(edit, " or ", newtree, " or ", newfile)
        rows = filter(None, [comment, span])
        trees = db(stree.study==study).select(stree.id,stree.type)
        if trees:
            for x in trees:
                a = A(x.type, _href=URL(c="stree",f="v",args=[x.id]))
                rows.append(a)
        tbl = UL(*[ LI(x) for x in rows ])

    return tbl

def editfile():
    f = db.study_file(request.args(0)) or redirect(URL("index"))
    def w(field, value):
        u = URL(c="study",f="view",args=[f.study])
        return A(_study_rep(f.study), _href=u)
    db.study_file.study.widget = w
    fields = ["study", "description", "source", "file", "data", "comment"]
    readonly = not auth.has_membership(role="contributor")
    form = SQLFORM(db.study_file, f, showid=False, fields=fields,
                   deletable=True, upload=URL(r=request,f='download'),
                   readonly=readonly)
    form.vars.study = f.study
    if request.vars.file:
        form.vars.filename = request.vars.file.filename
    if form.accepts(request.vars, session):
        response.flash = "record updated"
        redirect(URL(c="study",f="view",args=[f.study]))
    return dict(form=form)

#@auth.requires_membership('contributor')
@auth.requires_login()
def addfile():
    study = db.study(request.args(0)) or redirect(URL("index"))
    def w(field, value):
        u = URL(c="study",f="view",args=[study.id])
        return A(_study_rep(study), _href=u)
    t = db.study_file
    t.study.widget = w
    t.uploaded.readable=False
    ## form = crud.create(t)
    form = SQLFORM(t, fields=["study","description","source","file","comment"])
    form.vars.study=study.id
    name = "%s %s" % (auth.user.first_name, auth.user.last_name)
    form.vars.contributor = name
    if request.vars.file != None:
        form.vars.filename = request.vars.file.filename
    if form.accepts(request.vars, session):
        redirect(URL(c="study",f="view",args=[study.id]))
    return dict(form=form)

def index_ajax():
    response.subtitle = A("Studies", _href=URL(c='study',f="index"))
    t = db.study
    cit = Field("citation")
    t.year_published.requires = IS_NULL_OR(IS_IN_SET(
        [ x.year_published for x in
          db(t.id>0).select(t.year_published, orderby=t.year_published,
                            distinct=True) ]
        ))
    t.contributor.requires = IS_NULL_OR(IS_IN_SET(
        [ x.contributor for x in
          db(t.id>0).select(t.contributor, orderby=t.contributor,
                            distinct=True) ]
        ))
    form = SQLFORM.factory(
        cit, t.year_published, t.contributor,
        _id="searchform", _action=URL(c="study", f="search.load")
        )
    return dict(form=form)

def recent():
    t = db.study
    rows = db(t.id>0).select(t.ALL, limitby=(0,10), orderby=~t.uploaded)
    ## for rec in recent:
    ##     u = URL(c="study",f="view",args=[rec.id])
    ##     a = A(rec.citation, _href=u)
    ##     records.append(a)
    return dict(records=rows)

def search():
    t = db.study
    q = (t.id>0)
    for k, v in [ (k, v) for k, v in request.vars.items()
                  if (k in t.fields) ]:
        if v:
            q &= (t[k].like("%"+v+"%"))
    fields = (t.id, t.citation, t.year_published, t.uploaded)
    rows = db(q).select(*fields)
    headers = dict(
        [ (str(x), (str(x).split(".")[1]).capitalize().replace("_", " "))
          for x in fields ]
        )
    results = SQLTABLE2(rows, headers=headers)
    return dict(results=results)

def load_record():
    i = int(request.args(0) or 0)
    return LOAD("study", "record.load", args=[i], vars=request.vars, ajax=True)
    
@auth.requires_membership('contributor')
def record():
    t = db.study
    rec = t(int(request.args(0) or 0))
    ## t.focal_clade.readable = t.focal_clade.writable = False
    t.focal_clade_ott.label = 'Focal clade'
    t.focal_clade_ott.widget = SQLFORM.widgets.autocomplete(
        request, db.ott_name.unique_name, id_field=db.ott_name.node,
        limitby=(0,20), orderby=db.ott_name.unique_name)
    form = SQLFORM(t, rec, _id="recordform", showid=False)
    v = [ LI(A(tr.type, _target="_blank",
               _href=URL(c="stree", f="html", args=[tr.id], extension="")))
          for tr in db(db.stree.study==rec).select() ]
    trees = UL(*v)
    if form.accepts(request):
        response.flash = "record updated"
    return dict(form=form, trees=trees)


@auth.requires_membership('contributor')
def create():
    t = db.study
    name = "%s %s" % (auth.user.first_name, auth.user.last_name)
    t.contributor.default = name
    t.focal_clade_ott.label = 'Focal clade'
    t.focal_clade_ott.comment = 'Optional. Name of ingroup clade, if any'
    t.focal_clade_ott.widget = SQLFORM.widgets.autocomplete(
        request, db.ott_name.unique_name, id_field=db.ott_name.node,
        limitby=(0,20), orderby=db.ott_name.unique_name)
    t.citation.comment = ('Author surnames and publication titles '
                          'spelled out in full, to facilitate searching')
    t.doi.comment = SPAN(INPUT(_id="populate_from_doi", _type="button", _name="populate_from_doi", _value="Populate fields from DOI"), SPAN(_id="doi_ajax_spinner", _class="qq-upload-spinner", _hidden="true"))

    t.label.comment = ('Optional short descriptive phrase, e.g. '
                       '"Supertree of mammals". '
                       '(Perhaps should be deprecated in favor of tags.)')
    t.year_published.comment = '4-digit number'
    t.comment.label = 'Comments'
    t.comment.comment = 'Optional. Any miscellaneous notes'
    t.treebase_id.comment = 'Optional. Integer value'
    t.uploaded.readable = False
    form = crud.create(t, next="view/[id]")
    return dict(form=form)

def view():
    t = db.study
    rec = t(request.args(0)) or redirect(URL("create"))
    readonly = not auth.has_membership(role="contributor")
    t.doi.label = "DOI"
    # make read-only DOIs into proper hyperlinks
    if readonly:
        t.doi.represent = lambda v: A(doi2url(v), _href=doi2url(v), _target='_blank')
    ## t.focal_clade.readable = t.focal_clade.writable = False
    t.focal_clade_ott.label = 'Focal clade'
    t.focal_clade_ott.widget = SQLFORM.widgets.autocomplete(
        request, db.ott_name.unique_name, id_field=db.ott_name.node,
        limitby=(0,20), orderby=db.ott_name.unique_name)
    if rec.treebase_id:
        t.treebase_id.comment = A(
            "Import from TreeBASE", _class="button",
            _href=URL('study','tbimport',args=rec.treebase_id))
    form = SQLFORM(t, rec, deletable=False, readonly=readonly,
                   fields = ["citation", "year_published", "doi", "label",
                             "focal_clade_ott", "treebase_id",
                             "contributor", "comment", "uploaded"],
                   showid=False, submit_button="Update record")
    ## name = "%s %s" % (auth.user.first_name, auth.user.last_name)
    ## form.vars.contributor = name

    if form.accepts(request.vars, session):

        for ( attr, value ) in rec.as_dict().iteritems():

            if( attr not in form.vars ):
                continue

            if( str( form.vars[attr] ) != str( rec[attr] ) ):

                db.userEdit.insert( userName = ' '.join( [ auth.user.first_name, auth.user.last_name ] ),
                                    tableName = 'study',
                                    rowId = rec.id,
                                    fieldName = attr,
                                    previousValue = str( rec[attr] ),
                                    updatedValue = str( form.vars[attr] ) )

        ## not needed; mysql field is updated automatically
        ## rec.update_record( last_modified = datetime.datetime.now() )

        response.flash = "record updated"

    label = _study_rep(rec)
    trees = db(db.stree.study==rec.id).select()
    for f in ("study", "source", "data", "uploaded", "contributor",
              "filename"):#, "comment":
        db.study_file[f].readable=False
        db.study_file[f].writable=False
    db.study_file.file.label = ""
    db.study_file.id.label = "File"
    ## db.study_file.id.represent = lambda v: v.description
    if auth.has_membership(role="contributor"):
        r = lambda v: A("[Edit file info]", _href=URL(c="study",f="editfile",args=[v]))
        db.study_file.id.represent = r
    files = crud.select(db.study_file, db.study_file.study==rec, truncate=64)
    
    ### determines if there are json files matching the trees for the given study
    working_dir = os.path.dirname(os.path.realpath(__file__))
    working_dir = working_dir[:-11]
    working_dir = str(working_dir)
    working_dir_ncbi = working_dir + "static/taxonomy-stree-json/ncbi/"
    working_dir_ott = working_dir + "static/taxonomy-stree-json/ott/"
    dirlist_ncbi = os.listdir(working_dir_ncbi)# get list of files in working_directory
    dirlist_ott = os.listdir(working_dir_ott)# get list of files in working_directory
    graphlist_ncbi = []
    graphlist_ott = []
    for t in trees:
        treeid = str(t.id)
        file_name_ncbi = working_dir_ncbi + "tree_" + treeid + ".JSON" #build filename variable 
        file_name_ott = working_dir_ott + "tree_" + treeid + ".JSON" #build filename variable 
        try:
            with open(file_name_ncbi):
                graphlist_ncbi.append(treeid)
            with open(file_name_ott):
                graphlist_ott.append(treeid)
        except IOError:                        
            error = "No Json Found" ##do nothing

    return dict(form=form, label=label, trees=trees, files=files, rec=rec, graphlist_ncbi=graphlist_ncbi, graphlist_ott=graphlist_ott)
        
def delete_tag():
    rec = db.study(request.args(0))
    db.study_tag(request.args(1)).delete_record()
    return dict()

def tag():
    t = db.study_tag
    rec = db.study(request.args(0))
    tags = db(t.study==rec.id).select(orderby=t.tag)
    t.study.readable = t.study.writable = False
    t.tag.label = 'Add'
    t.study.default = rec.id
    t.tag.widget = SQLFORM.widgets.autocomplete(request, t.tag)
    form = SQLFORM(t)
    if form.process(message_onsuccess=None).accepted:
        tags = db(t.study==rec.id).select(orderby=t.tag)
    v = []
    for t in tags:
        u = URL('study', 'delete_tag.load', args=[rec.id, t.id])
        cid = 'study-tag-%s' % t.id
        a = A("[X]", _href=u, cid=cid, _title='delete tag')
        v.append(SPAN(t.tag, XML('&nbsp;'), a, _id=cid))
    return dict(tags=v, form=form)

def download():
    return response.download(request, db)

def to_nexml():
    if len(request.args) == 1:
        _LOG = get_logger(request, 'study')
        try:
            field = db['study_file']['file']
        except Error:
            sys.stderr.write('odd\n')
            raise HTTP(404)
        name = request.args[-1]
        sys.stderr.write('looking for file "' + name + '"\n')
        try:
            ext_proc_dir = get_external_proc_dir_for_upload(request, db, name)
        except ValueError:
            raise HTTP(404)
        if ext_proc_dir is None:
            raise HTTP(404)

        #@TEMPORARY could be refactored into a create_ext_proc_subdir() call
        to_nexml_dir = os.path.join(ext_proc_dir, '2nexml')
        if not os.path.exists(to_nexml_dir):
            os.makedirs(to_nexml_dir)
            _LOG.info('Created directory "%s"' % to_nexml_dir)
        block = True
        timeout_duration = 0.1 #@TEMPORARY should not be hard coded

        out_filename = 'out.xml'
        err_filename = 'err.txt'

        #@TEMPORARY could be refactored into a launch_or_get_status() call
        status = invoc_status(request, to_nexml_dir)
        launched_this_call = False
        if status == ExternalProcStatus.NOT_FOUND:
            try:
                try:
                    exe_path = get_conf(request).get("external", "2nexml")
                except:
                    _LOG.warn("Config does not have external/2nexml setting")
                    raise
                assert(os.path.exists(exe_path))
            except:
                _LOG.warn("Could not find the 2nexml executable")
                raise HTTP(501, T("Server is not configured to allow 2nexml conversion"))
            try:
                (filename, upload_stream) = field.retrieve(name)
            except IOError:
                sys.stderr.write('not found\n')
                raise HTTP(404)
            do_ext_proc_launch(request,
                               to_nexml_dir,
                               [exe_path, 'in.nex'],
                               out_filename,
                               err_filename,
                               [('in.nex', upload_stream)],
                               wait=block)
            if not block:
                time.sleep(timeout_duration)
            status = invoc_status(request, to_nexml_dir)
            assert(status != ExternalProcStatus.NOT_FOUND)
            launched_this_call = True
        if status == ExternalProcStatus.RUNNING:
            if not launched_this_call:
                time.sleep(timeout_duration)
                status = invoc_status(request, to_nexml_dir)
            if status == ExternalProcStatus.RUNNING:
                return HTTP(102, T("Process still running"))
        #@TEMPORARY /end of potential launch_or_get_status call...
        
        if status == ExternalProcStatus.FAILED:
            try:
                err_file = os.path.join(to_nexml_dir, err_filename)
                err_content = 'Error message:\n ' + open(err_file, 'rU').read()
            except:
                err_content = ''
            response.headers['Content-Type'] = 'text/xml'
            raise HTTP(501, T("Conversion to NeXML failed.\n" + err_content))
        output = os.path.join(to_nexml_dir, 'out.xml')
        response.headers['Content-Type'] = 'text/xml'
        return open(output, 'rU').read()
        
    else:
        raise HTTP(301)
    return response.download(request, db)

def strees():
    rows = db(db.stree.study==int(request.args(0) or 0)).select()
    return dict(trees=rows)

@auth.requires_membership('contributor')
def tbimport():
    t = db.study
    key = "uploaded_nexml_%s" % auth.user.id
    contributor = "%s %s" % (auth.user.first_name, auth.user.last_name)
    status = None
    tbid = request.args(0)
    if tbid:
        try:
            e = treebase.fetch_study(tbid)
            nexml = treebase.parse_nexml(e)
        except:
            nexml = { }
            status = "Valid study id required"
        if nexml:
            nexml.meta['contributor'] = contributor
            cache.ram.clear(key)
            x = cache.ram(key, lambda:nexml, time_expire=10000)
            redirect(URL('study','tbimport2',args=tbid))
    uploadfolder = request.folder+'uploads'
    fields = [Field("study_id", "string", default=tbid),
              Field("nexml_file", "upload", uploadfolder=uploadfolder)]
    form = SQLFORM.factory(*fields)
    if form.accepts(request.vars, session, dbio=False):
        if form.vars.study_id:
            try:
                e = treebase.fetch_study(form.vars.study_id)
                nexml = treebase.parse_nexml(e)
            except:
                nexml = { }
                status = "Valid study id required"
        elif form.vars.nexml_file:
            ## print form.vars.nexml_file
            path = os.path.join(uploadfolder,
                                form.vars.nexml_file)
                                ## form.vars.nexml_file_newfilename)
            nexml = treebase.parse_nexml(path)
            os.remove(path)
        else:
            nexml = {}
            request.flash = "Valid study id or nexml file required"
        if nexml:
            nexml.meta['contributor'] = contributor
            cache.ram.clear(key)
            x = cache.ram(key, lambda:nexml, time_expire=10000)
            redirect(URL('study','tbimport2',args=tbid))

    return dict(form=form, status=status )

@auth.requires_membership('contributor')
def tbimport2():
    tbid = request.args(0)
    t = db.study
    ## t.focal_clade.readable = t.focal_clade.writable = False
    t.focal_clade_ott.label = 'Focal clade'
    t.focal_clade_ott.widget = SQLFORM.widgets.autocomplete(
        request, db.ott_name.unique_name, id_field=db.ott_name.node,
        limitby=(0,20), orderby=db.ott_name.unique_name)
    t.uploaded.readable=False
    key = "uploaded_nexml_%s" % auth.user.id
    nexml = cache.ram(key, lambda:None, time_expire=10000)
    if not nexml:
        session.flash = "Please upload the Nexml file again"
        redirect(URL('study','tbimport'))
    cache.ram(key, lambda:nexml, time_expire=10000)
    ## assert nexml
    ## cache.ram.clear(key)
    get = lambda x: nexml.meta.get(x) or None
    treebase_id = int(get('tb:identifier.study'))
    rec = db(t.treebase_id==treebase_id).select().first()
    year = int(get('prism:publicationDate') or 0)
    d = dict(citation = get('dcterms:bibliographicCitation'),
             year_published = year if year else None,
             label = get('tb:title.study'),
             doi = get('prism:doi'),
             treebase_id = treebase_id,
             contributor = get('contributor'))

    diffs = []
    if rec: # edit an existing study record
        if not tbid: response.flash = "Record exists: study id = %s" % rec.id
        diffs = [ (k, v) for k, v in d.items()
                  if rec[k] != v and k != 'contributor' ]
        form = SQLFORM(t, rec, showid=False, submit_button="Update study")

    else:
        for k, v in d.items():
            if v and k in t.fields: t[k].default = v
        form = SQLFORM(t, submit_button="Insert study")
    
    ## form = crud.create(t, next="view/[id]")
    if form.accepts(request.vars, session):
        if rec: response.flash = "record updated"
        else: response.flash = "record inserted"
        ## t.update_record( last_modified = datetime.datetime.now() )
        ## redirect(URL('study','view',args=form.vars.id))

    return dict(form=form, rec=rec, diffs=diffs)

def tbimport_otus():
    theme = "smoothness"
    for x in (
        # 'DataTables-1.8.1/media/js/jquery.js',  # there's already a newer (Bootstrap-compatible) jQuery loaded!
        'DataTables-1.8.1/media/js/jquery.dataTables.min.js',
        'DataTables-1.8.1/media/css/bootstrap_table.css',
        'DataTables-1.8.1/media/ui/css/%s/jquery-ui-1.8.5.custom.css' % theme):
        response.files.append(URL('static',x))

    t = db.study
    ## t.focal_clade.readable = t.focal_clade.writable = False
    t.focal_clade_ott.label = 'Focal clade'
    t.focal_clade_ott.widget = SQLFORM.widgets.autocomplete(
        request, db.ott_name.unique_name, id_field=db.ott_name.node,
        limitby=(0,20), orderby=db.ott_name.unique_name)
    t.uploaded.readable=False
    key = "uploaded_nexml_%s" % auth.user.id
    nexml = cache.ram(key, lambda:None, time_expire=10000)
    if not nexml:
        session.flash = "Please upload the Nexml file again"
        redirect(URL('study','tbimport'))
    cache.ram(key, lambda:nexml, time_expire=10000)
    otus = [ (k, Storage(v)) for k,v in sorted(nexml.otus.items()) ]
    get = lambda x: nexml.meta.get(x) or None
    treebase_id = int(get('tb:identifier.study'))
    rec = db(t.treebase_id==treebase_id).select().first()
    if not rec:
        session.flash = 'Study record needed!'
        redirect(URL('study','tbimport2'))

    # figure out if OTUs already exist for this study
    left = db.ott_node.on(db.otu.ott_node==db.ott_node.id)
    rows = db(db.otu.study==rec.id).select(db.otu.ALL, db.ott_node.ALL,
                                           left=left)
    ## d = dict([ (x.ott_node.treebase, x.otu.id)
    ##            for x in rows if x.ott_node and x.ott_node.treebase ])
    ## d.update(dict([ (x.otu.label, x.otu) for x in rows ]))
    d = dict([ (x.otu.label, x.otu) for x in rows ])
    d.update(dict([ (x.otu.tb_nexml_id, x.otu) for x in rows ]))
        
    existing = [ not ((v.label in d) or (v.id in d))
                 for k, v in otus ]
    for k, v in otus:
        o = nexml.otus[k]
        o.otu = d.get(v.id) or d.get(v.label)

    colnames = ["Nexml id", "Label", "NCBI taxid", "NameBank id",
                "Taxon match?", "New?"]
    colwidths = [ "15%", "30%", "15%", "15%", "15%", "10%"]
    
    # figure out if uploaded OTUs have matching taxon records
    q = (db.ott_node.name.belongs([ v.label for k,v in otus ])|
         db.ott_node.ncbi.belongs([ int(v.ncbi_taxid) for k,v in otus
                                    if v.ncbi_taxid ]))
    rows = db(q).select()
    matches = dict([ (x.name, x.id) for x in rows ])
    matches.update(dict([ (x.ncbi, x.id) for x in rows if x.ncbi ]))
    matchv = [ bool((v.name in matches) or
                    (v.ncbi and v.ncbi in matches))
               for k,v in otus ]

    tid = "otus"
    table = TABLE(_id=tid,_class="display")
    table.append(THEAD(TR(*[ TH(c, _width=w) for c, w in
                             zip(colnames, colwidths) ])))
    rows = [ TR(TD(v.id), TD(v.label), TD(v.ncbi_taxid or ""),
                TD(v.namebank_id or ""),
                INPUT(_type='checkbox',value=m, _disabled="disabled"),
                INPUT(_type='checkbox',value=bool(e), _disabled="disabled"))
             for (k, v), m, e in zip(otus, matchv, existing) ]
    table.append(TBODY(*rows))

    new_otus = [ v for (k,v),e in zip(otus, existing) if e ]
    if new_otus:
        value = "|".join([ x.id for x in new_otus ])
        form = FORM(INPUT(_type="hidden",_name="_import",_value=value),
                    INPUT(_type="submit",
                          _value="Import %s new OTUs" % len(new_otus)))
        if request.vars._import:
        ## if form.accepts(request.vars, session):
            v = request.vars._import.split("|")
            n = 0
            for k in v:
                x = Storage(nexml.otus[k])
                ## t = (new_tb_taxids.get(x.treebase_taxid) or
                ##      new_ncbi_taxids.get(x.ncbi_taxid) or
                ##      new_labels.get(x.label))
                t = matches.get(x.label) or matches.get(x.ncbi_taxid)
                if t:
                    r = db.ott_node[t]
                    ## if not r.treebase and x.treebase_taxid:
                    ##     r.update_record(treebase_taxid=x.treebase_taxid)
                    if not r.ncbi and x.ncbi_taxid:
                        r.update_record(ncbi=x.ncbi_taxid)
                    ## if not r.namebank_taxid and x.namebank_taxid:
                    ##     r.update_record(namebank_taxid=x.namebank_taxid)
                i = db.otu.insert(study=rec.id, label=x.label, ott_node=t,
                                  tb_nexml_id=x.id)
                if i:
                    nexml.otus[k]['otu'] = db.otu[i]
                    n += 1
                ## else:
                ##     print x.label, t

            session.flash = "%s OTUs inserted" % n
            redirect(URL('study','tbimport_otus'))
    else:
        form = ""
        
    return dict(nexml=nexml, table=table, tid=tid, form=form, rec=rec)

def fetch_treebase_nexml():
    sid = request.args(0)
    e = treebase.fetch_study(sid)
    response.headers["Content-Type"] = "text/xml"
    s = "attachment; filename=TB-study-%s.nexml" % sid
    response.headers["Content-Disposition"] = s
    buf = StringIO()
    e.write(buf, pretty_print=True)
    return buf.getvalue()

def tbimport_trees():
    t = db.study
    key = "uploaded_nexml_%s" % auth.user.id
    ## nexml = cache.ram(key, lambda:None, time_expire=10000)
    nexml = cache.ram(key, lambda:None, time_expire=10000)
    if not nexml:
        session.flash = "Please upload the Nexml file again"
        redirect(URL('study','tbimport'))
    cache.ram(key, lambda:nexml, time_expire=10000)
    get = lambda x: nexml.meta.get(x) or None
    treebase_id = int(get('tb:identifier.study'))
    rec = db(t.treebase_id==treebase_id).select().first()
    if not rec:
        session.flash = 'Study record needed!'
        redirect(URL('study','tbimport2'))

    for tree in nexml.trees:
        stree = db(db.stree.tb_tree_id==tree.attrib.id).select(db.stree.id).first()
        if not stree:
            tree.importform = FORM(
                INPUT(_type='hidden',_name='treeid',_value=tree.attrib.id),
                INPUT(_type='submit',_value='import tree'),
                _action=URL('stree','import_cached_nexml',args=tree.attrib.id)
                )
        else:
            tree.importform = A("Imported", _href=URL('stree','svgView',args=stree.id))
            
    return dict(rec=rec, trees=nexml.trees)

def ref_from_doi():
    """
    This controller is expecting two arguments (because DOI's contain /
    Try 
        DOMAIN_NAME/phylografter/study/ref_from_doi/10.1111/j.1463-6409.2009.00419.x.json
    It returns a JSON procite object with "citation" and "year" fields added
    
    The intention is for this to be called by the study/create view when the user
    wants to try to fill in fields based on the DOI.  It seems to be better to
    wrap this call to an external service here so that the jQuery won't be concerned about
    cross-site scripting in the AJAX code for updating the create form.
    """
    def format_citation(d):
        '''
        Parses the output of the procite (vnd.citationstyles.csl+json) format
        into a citation and year (as string)
        '''
        o = StringIO()
        authors_written = False
        for n, author in enumerate(d.get("author", [])):
            if n != 0:
                o.write(u", ")
            given_name = unicode(author.get("given", ""))
            family_name = unicode(author.get("family", ""))
            if family_name:
                if given_name:
                    o.write(given_name)
                    o.write(u" ")
                o.write(family_name)
            elif given_name:
                o.write(given_name)
            authors_written = True
        if authors_written:
            o.write(u". ")
        # issue["date-parts"] is as list of [year, month] objects, I think...
        year = unicode(d.get("issued",{}).get("date-parts",[[""],])[0][0])
        if year:
            o.write(year)
            o.write(u". ")
        title = unicode(d.get("title", ""))
        if title:
            o.write(title)
            o.write(u'. ')
        journal = unicode(d.get("container-title", ""))
        if journal:
            o.write(journal)
            o.write(u" ")
        volume = unicode(d.get("volume", ""))
        if volume:
            o.write(volume)
        issue = unicode(d.get("issue", ""))
        if issue:
            o.write(u"(" + issue + u")")
        if issue or volume:
            o.write(u":")
        page = unicode(d.get("page", ""))
        if page:
            o.write(page)
            o.write(u".")
        return u' '.join(o.getvalue().split()), year

    if len(request.args) < 2:
        response.status = 404
        response.write('Execting a DOI with at least one / in it')
        return
    raw = '/'.join(list(request.args))
    DOMAIN = 'http://dx.doi.org'
    doi = normalize_doi_for_url(raw)
    #sys.stderr.write('About look up reference for the doi "%s"\n' % doi)
    RETURNS_OBJECT = True
    SUBMIT_URI = DOMAIN + '/' + doi
    payload = {
    }
    headers = {
    }
    if RETURNS_OBJECT:
        headers['content-type'] = 'application/json'
        headers['Accept'] = 'application/vnd.citationstyles.csl+json, application/rdf+json'
        requested_formats = "JSON citeproc or RDF"
    else:
        headers['content-type'] = 'application/tex'
        headers['Accept'] = 'text/x-bibliography; style=apa'
        requested_formats = "Bibliographic citation (text; style=APA)"
    #sys.stderr.write('Sending GET to "%s"\n' % (SUBMIT_URI))
    resp = requests.get(SUBMIT_URI,
                        params=payload,
                        headers=headers,
                        allow_redirects=True)
    #sys.stderr.write('Sent GET to %s\n' %(resp.url))
    if resp.status_code == 404:
        sys.stderr.write('Requested DOI, "%s", does not exist\n' % doi)
        response.status = 404
        return
    if resp.status_code == 406:
        sys.stderr.write('DOI found, but unavailable in the requested format(s): %s\n' % requested_formats)
        response.status = 406
        return
    if resp.status_code == 204:
        sys.stderr.write('DOI found, but no bibliographic information was available')
        response.status = 204
        return
    resp.raise_for_status()
    if RETURNS_OBJECT:
        # Hm, sometimes resp.json is an instance method, and sometimes it's a dict. Be careful!
        try:
            results = resp.json()
        except: 
            results = resp.json
        #sys.stderr.write('%s\n' % json.dumps(results, sort_keys=True, indent=4))
        #sys.stderr.write('%s\n' % str(dict(results)))
        if results is None:
            sys.stderr.write('Requested DOI, "%s", does not exist\n' % doi)
            response.status = 404
            return
        d = dict(results)
        citation, year = format_citation(d)
        d['citation'] = citation
        d['year'] = year
        return d
    else:
        print resp.text

@service.json
def fetch_nexson(study_id):
    try: study_id = int(study_id)
    except ValueError: raise HTTP(404)
    if not db.study(study_id): raise HTTP(404)
    return nexson.nexmlStudy(study_id,db)

def call():
    return service()

def export_NexSON():
    'Exports the otus and trees in the study specified by the argument as JSON NeXML'
    studyid = request.args(0)
    if (db.study(studyid) is None):
        raise HTTP(404)
    else:
        return nexson.nexmlStudy(studyid,db)

#some overlap with corresponding function in stree.py    
def modified_list():
    'This reports a json formatted list of ids of modified studies'
    dtimeFormat = '%Y-%m-%dT%H:%M:%S'
    fromString = request.vars['from']
    if fromString is None:
        fromTime = datetime.datetime.now() - datetime.timedelta(1)
    else:
       fromTime = datetime.datetime.strptime(fromString,dtimeFormat)
    toString = request.vars['to']
    if toString is None:
        toTime = datetime.datetime.now()
    else:
        toTime = datetime.datetime.strptime(toString,dtimeFormat)
    #look for studies with uploaded in the interval
    upLoadQuery = (db.study.uploaded > fromTime) & (db.study.uploaded <= toTime) 
    studies = set()
    for s in db(upLoadQuery).select():
        studies.add(s.id)
    #as well as studies modified within the interval
    timeQuery = (db.study.last_modified > fromTime) & (db.study.last_modified <= toTime)
    for s in db(timeQuery).select():
        studies.add(s.id)
    #assuming that a tree can't be uploaded independently of a study, it might still be modified
    #so this checks for strees modified in the interval and adds their study ids to the list
    treeQuery = (db.stree.last_modified > fromTime) & (db.stree.last_modified <= toTime)
    for t in db(treeQuery).select():
        studies.add(t.study)        
    studyList = list(studies)
    wrapper = dict(studies = studyList)
    wrapper['from']=fromTime.strftime(dtimeFormat)
    wrapper['to']=toTime.strftime(dtimeFormat)
    return wrapper

def export_csv():
    studies = db().select(db.study.ALL)
    return dict(studies=studies)

def export_gzipNexSON():
    'Exports the otus and trees in the study specified by the argument as gzipped JSON NeXML'
    studyid = request.args(0)
    if (db.study(studyid) is None):
        raise HTTP(404)
    else:
        from gluon.serializers import json
        import cStringIO
        stream = cStringIO.StringIO()
        jsondict = nexson.nexmlStudy(studyid,db)
        jsonText = json(jsondict)
        zipfilename = "study%s.json.gz" % studyid
        gzfile = gzip.GzipFile(filename=zipfilename, mode="wb", fileobj=stream)
        gzfile.write(jsonText)
        gzfile.write("\n")
        gzfile.close() 
        response.headers['Content-Type'] = "application/gzip"
        response.headers['Content-Disposition'] = "attachment;filename=%s"%zipfilename
        return stream.getvalue()              
    return
 
### Function to allow the deletion of a study and all of its corresponding nodes, trees and otus
    
def delete_study():
    'Displays a page to ask for validation before deleting a study that is actively being viewed'
    t = db.study
    rec = t(request.args(0)) or redirect(URL("create"))
    readonly = not auth.has_membership(role="contributor")
    ## t.focal_clade.readable = t.focal_clade.writable = False
    t.focal_clade_ott.label = 'Focal clade'
    t.focal_clade_ott.widget = SQLFORM.widgets.autocomplete(
        request, db.ott_name.unique_name, id_field=db.ott_name.node,
        limitby=(0,20), orderby=db.ott_name.unique_name)
    form = SQLFORM(t, rec, deletable=False, readonly=False,
                   fields = ["citation", "year_published", "doi", "label",
                             "focal_clade_ott", "treebase_id",
                             "contributor", "comment", "uploaded"],
                   showid=False, submit_button="Delete Study")
    form.add_button('Cancel', URL('study', 'view', args=rec.id))
                       
    

    if form.accepts(request.vars, session):
	## Deletes the study from the database using the DAL. 
        del db.study[rec.id]

        session.flash = "The Study Has Been Deleted" #Alerts the user the study has been deleted.	
        redirect(URL('study', 'index'))
    return dict(form=form, rec = rec)
