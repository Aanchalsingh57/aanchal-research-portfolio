"""Additional CMS write-path and data-integrity checks. Fixtures are tests only."""
import pytest
from datetime import date
from app.extensions import db
from app.models import *

CASES=[
 ('interests',ResearchInterest,{'title':'Test-only interest','kind':'aiml','sort_order':'2','is_published':'y'},'title'),
 ('skills',Skill,{'name':'Test-only skill','category':'Computational and Data','proficiency':'Learning','project_id':'0','sort_order':'1','is_published':'y'},'name'),
 ('education',Education,{'degree':'Test-only degree','institution':'Test fixture institution','sort_order':'1','is_published':'y'},'degree'),
 ('experience',Experience,{'role':'Test-only role','organization':'Test fixture organization','project_id':'0','sort_order':'1','is_published':'y'},'role'),
 ('publications',Publication,{'title':'Test-only output','slug':'test-only-output','status':'Under Review','output_type':'Preprint','year':'2026','project_id':'0','interest_id':'0','sort_order':'1','is_published':'y'},'title'),
 ('achievements',Achievement,{'title':'Test-only milestone','organization':'Test fixture organization','sort_order':'1','is_published':'y'},'title'),
 ('notes',BlogPost,{'title':'Test-only note','slug':'test-only-note','publication_date':'2026-10-26','content':'## Test fixture\n\nNo actual research findings.','cover_id':'0','sort_order':'1','is_published':'y'},'title'),
 ('links',SocialLink,{'label':'Test-only profile','url':'https://example.com/qa','sort_order':'1','is_published':'y'},'label')]

@pytest.mark.parametrize('kind,model,data,label_field',CASES)
def test_collection_write_update_delete(app,admin,kind,model,data,label_field):
    response=admin.post('/admin/content/'+kind+'/new',data=data)
    assert response.status_code==302,response.get_data(as_text=True)
    with app.app_context():
        item=db.session.scalar(db.select(model).where(getattr(model,label_field)==data[label_field]));assert item is not None
        identity=item.id;assert item.is_published
    updated={**data,label_field:data[label_field]+' updated'}
    response=admin.post(f'/admin/content/{kind}/{identity}/edit',data=updated)
    assert response.status_code==302,response.get_data(as_text=True)
    with app.app_context():assert getattr(db.session.get(model,identity),label_field)==updated[label_field]
    assert admin.get('/').status_code==200
    assert admin.post(f'/admin/content/{kind}/{identity}/delete').status_code==302
    with app.app_context():assert db.session.get(model,identity) is None

def test_profile_update_with_optional_fields(app,admin):
    response=admin.post('/admin/profile',data={'name':'Aanchal Singh','headline':'Reviewed test headline','degree':'M.Tech Biotechnology','institution':'NIT Jalandhar','biography':'Test-only biography update.','email':'public@example.com','photo_id':'0','cv_id':'0'})
    assert response.status_code==302,response.get_data(as_text=True)
    with app.app_context():assert db.session.get(Profile,1).headline=='Reviewed test headline'
    assert 'Reviewed test headline' in admin.get('/').get_data(as_text=True)

def test_seed_respects_intentionally_removed_defaults(app):
    with app.app_context():
        db.session.execute(db.delete(ResearchInterest));db.session.execute(db.delete(Education));db.session.commit()
    assert app.test_cli_runner().invoke(args=['seed']).exit_code==0
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count()).select_from(ResearchInterest))==0
        assert db.session.scalar(db.select(db.func.count()).select_from(Education))==0

def test_notes_require_real_publication_date(app,admin):
    response=admin.post('/admin/content/notes/new',data={'title':'Test-only note','slug':'needs-date','content':'Fixture only.','cover_id':'0','sort_order':'0','is_published':'y'})
    assert response.status_code==200 and 'Set the actual publication date' in response.get_data(as_text=True)
    with app.app_context():assert db.session.scalar(db.select(BlogPost).where(BlogPost.slug=='needs-date')) is None

def test_asset_quota(app,admin):
    from PIL import Image
    from io import BytesIO
    output=BytesIO();Image.new('RGB',(40,40),'teal').save(output,format='PNG');output.seek(0)
    app.config['MAX_ASSET_TOTAL_BYTES']=1
    response=admin.post('/admin/assets',data={'file':(output,'fixture.png'),'kind':'image','alt_text':'Test-only image'},content_type='multipart/form-data')
    assert 'storage quota' in response.get_data(as_text=True)
    with app.app_context():assert db.session.scalar(db.select(db.func.count()).select_from(UploadedAsset))==0

def test_relation_nulling_does_not_delete_child_records(app,admin):
    with app.app_context():
        interest=ResearchInterest(title='Test-only relation');db.session.add(interest);db.session.flush()
        project=Project(title='Test-only relation project',slug='relation',interest_id=interest.id)
        db.session.add(project);db.session.flush();pid=project.id;iid=interest.id
        skill=Skill(name='Test-only relational skill',category='AI/ML',project_id=pid)
        db.session.add(skill);db.session.flush();sid=skill.id;db.session.commit()
    assert admin.post(f'/admin/content/interests/{iid}/delete').status_code==302
    with app.app_context():assert db.session.get(Project,pid).interest_id is None
    assert admin.post(f'/admin/content/projects/{pid}/delete').status_code==302
    with app.app_context():assert db.session.get(Skill,sid).project_id is None

def test_server_rejects_whitespace_only_and_long_input(app,client):
    response=client.post('/contact',data={'name':'   ','email':'user@example.com','subject':'a'*181,'message':'x'*5001,'consent':'y'})
    assert response.status_code==200
    with app.app_context():assert db.session.scalar(db.select(db.func.count()).select_from(ContactMessage))==0
