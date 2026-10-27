import os
from urllib.parse import urlsplit
import pytest
from app import create_app
from app.extensions import db
from app.models import AdminUser

BACKENDS=['sqlite']+(['postgresql'] if os.getenv('TEST_POSTGRES_URL') else [])
@pytest.fixture(params=BACKENDS)
def app(request,tmp_path):
    if request.param=='postgresql':
        uri=os.environ['TEST_POSTGRES_URL']
        parts=urlsplit(uri)
        # Refuse remote or non-test databases: cleanup must never touch real user data.
        if parts.hostname not in (None,'localhost','127.0.0.1') or parts.path!='/portfolio_test':
            raise RuntimeError('TEST_POSTGRES_URL must be a local database named portfolio_test.')
    else:uri='sqlite:///'+str(tmp_path/'isolated-test.db')
    application=create_app({'TESTING':True,'APP_ENV':'testing','SQLALCHEMY_DATABASE_URI':uri,
        'SECRET_KEY':'test-only-strong-key-not-for-real-use','WTF_CSRF_ENABLED':False,
        'BASE_URL':'https://portfolio.example','TRUSTED_HOSTS':None,
        'MAIL_API_KEY':'','MAIL_FROM':'','MAIL_TO':''})
    with application.app_context():
        db.create_all()
        result=application.test_cli_runner().invoke(args=['seed'])
        assert result.exit_code==0,result.output
        user=AdminUser(email='admin@example.com');user.set_password('test-only-password-12345')
        db.session.add(user);db.session.commit()
    yield application
    with application.app_context():
        assert application.config['TESTING'] and application.config['APP_ENV']=='testing'
        db.session.remove();db.drop_all();db.engine.dispose()
@pytest.fixture
def client(app):return app.test_client()
@pytest.fixture
def admin(client):
    result=client.post('/admin/login',data={'email':'admin@example.com','password':'test-only-password-12345'})
    assert result.status_code==302
    return client
