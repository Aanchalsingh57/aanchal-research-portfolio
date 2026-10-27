from datetime import date, timedelta, datetime, timezone
from io import BytesIO
import re
import hashlib

import pytest
from PIL import Image
from sqlalchemy.exc import OperationalError

from app import create_app
from app.extensions import db
from app.models import *
from app.catalog import CATALOG
from tests.conftest import app


def store(app, model, **data):
    with app.app_context():
        obj = model(**data)
        db.session.add(obj)
        db.session.commit()
        return obj.id


def message_data(**overrides):
    data = {
        'name': 'Research Visitor',
        'email': 'visitor@example.com',
        'subject': 'Academic enquiry',
        'message': 'I would like to discuss biotechnology research interests.',
        'consent': 'y',
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize(
    'path',
    [
        '/', '/about', '/projects', '/publications', '/notes',
        '/contact', '/privacy', '/research/1', '/health',
        '/robots.txt', '/sitemap.xml', '/admin/login',
    ],
)
def test_public_routes(client, path):
    result = client.get(path)
    assert result.status_code == 200, (
        path, result.get_data(as_text=True)
    )


def test_profile_initial_facts(client, app):
    from app.models import Profile

    response = client.get('/')

    with app.app_context():
        profile = db.session.get(Profile, 1)
        print("TEST CV PATH:", repr(profile.cv_path) if profile else None)
        print("TEST CV ID:", profile.cv_id if profile else None)
        print(
            "TEST CV ASSET:",
            (profile.cv.filename, profile.cv.is_public)
            if profile and profile.cv else None,
        )

    body = response.get_data(as_text=True)
    assert 'Aanchal Singh' in body and 'M.Tech' in body and 'Jalandhar' in body
    assert 'Download CV' not in body


@pytest.mark.parametrize(
    'path',
    [
        '/missing', '/projects/missing', '/publications/missing',
        '/notes/missing', '/cv', '/cv/download', '/assets/9999',
        '/research/9999',
    ],
)
def test_missing_pages(client, path):
    assert client.get(path).status_code == 404


@pytest.mark.parametrize(
    'path',
    [
        '/admin/', '/admin/profile', '/admin/content/projects',
        '/admin/content/publications/new', '/admin/assets',
        '/admin/messages', '/admin/sections',
    ],
)
def test_admin_routes_require_login(client, path):
    r = client.get(path)
    assert r.status_code == 302 and '/admin/login' in r.location


@pytest.mark.parametrize('kind', ['projects', 'publications', 'notes'])
def test_visibility_and_preview(app, client, kind):
    model = {
        'projects': Project,
        'publications': Publication,
        'notes': BlogPost,
    }[kind]
    extras = {'publication_date': date.today()} if kind == 'notes' else {}

    store(
        app, model, title='Hidden draft', slug='hidden-draft',
        is_published=False, **extras,
    )
    store(
        app, model, title='Visible entry', slug='visible-entry',
        is_published=True, **extras,
    )

    assert client.get('/' + kind + '/hidden-draft').status_code == 404
    assert client.get('/' + kind + '/hidden-draft?preview=1').status_code == 404
    assert client.get('/' + kind + '/visible-entry').status_code == 200

    listing = client.get('/' + kind).get_data(as_text=True)
    assert 'Visible entry' in listing and 'Hidden draft' not in listing

    client.post(
        '/admin/login',
        data={
            'email': 'admin@example.com',
            'password': 'test-only-password-12345',
        },
    )
    preview = client.get('/' + kind + '/hidden-draft?preview=1')
    assert preview.status_code == 200
    assert 'PRIVATE ADMIN PREVIEW' in preview.get_data(as_text=True)
    assert preview.headers['Cache-Control'] == 'no-store'
    assert 'noindex' in preview.headers['X-Robots-Tag']


def test_login_logout(admin):
    assert admin.get('/admin/').status_code == 200
    assert admin.post('/admin/logout').status_code == 302
    assert admin.get('/admin/').status_code == 302


def test_invalid_login(client):
    r = client.post(
        '/admin/login',
        data={'email': 'admin@example.com', 'password': 'wrong'},
    )
    assert r.status_code == 200
    assert 'Invalid administrator credentials.' in r.get_data(as_text=True)
    assert client.get('/admin/').status_code == 302


def test_no_public_registration(client):
    assert client.get('/admin/register').status_code == 404


def test_non_admin_forbidden(app, client):
    with app.app_context():
        u = db.session.scalar(
            db.select(AdminUser).where(
                AdminUser.email == 'admin@example.com'
            )
        )
        u.role = 'viewer'
        db.session.commit()

    r = client.post(
        '/admin/login',
        data={
            'email': 'admin@example.com',
            'password': 'test-only-password-12345',
        },
    )
    assert 'Invalid administrator credentials.' in r.get_data(as_text=True)


@pytest.mark.parametrize('kind', list(CATALOG))
def test_admin_editors_render(admin, kind):
    path = (
        '/admin/profile'
        if kind == 'profile'
        else '/admin/content/' + kind + '/new'
    )
    r = admin.get(path)
    assert r.status_code == 200, r.get_data(as_text=True)


def test_admin_management_pages(admin):
    paths = [
        '/admin/', '/admin/assets', '/admin/messages', '/admin/sections',
    ] + [
        '/admin/content/' + key for key in CATALOG if key != 'profile'
    ]

    for path in paths:
        r = admin.get(path)
        assert r.status_code == 200, (path, r.get_data(as_text=True))


def project_form(**overrides):
    values = {
        'title': 'DEMONSTRATION fixture',
        'slug': 'fixture',
        'summary': 'Test-only project, not a real achievement.',
        'category': 'Biotechnology',
        'status': 'Planned',
        'interest_id': '0',
        'image_id': '0',
        'sort_order': '0',
    }
    values.update(overrides)
    return values


def test_project_crud(app, admin, client):
    r = admin.post('/admin/content/projects/new', data=project_form())
    assert r.status_code == 302, r.get_data(as_text=True)

    with app.app_context():
        p = db.session.scalar(
            db.select(Project).where(Project.slug == 'fixture')
        )
        pid = p.id
        assert not p.is_published

    r = admin.post(
        f'/admin/content/projects/{pid}/edit',
        data=project_form(
            title='Verified fixture',
            is_published='y',
            is_featured='y',
        ),
    )
    assert r.status_code == 302, r.get_data(as_text=True)
    assert 'Verified fixture' in admin.get('/').get_data(as_text=True)
    assert admin.get('/projects/fixture').status_code == 200
    assert admin.post(f'/admin/content/projects/{pid}/delete').status_code == 302
    assert admin.get('/projects/fixture').status_code == 404


def test_duplicate_slugs_and_input_safety(app, admin):
    store(app, Project, title='Original', slug='fixture')

    r = admin.post('/admin/content/projects/new', data=project_form())
    assert 'already in use' in r.get_data(as_text=True)

    r = admin.post(
        '/admin/content/projects/new',
        data=project_form(slug='Bad Slug'),
    )
    assert 'Use lowercase' in r.get_data(as_text=True)

    r = admin.post(
        '/admin/content/projects/new',
        data=project_form(repository_url='javascript:alert(1)'),
    )
    assert 'Use a complete' in r.get_data(as_text=True)

    r = admin.post(
        '/admin/content/projects/new',
        data=project_form(interest_id='99999'),
    )
    assert 'Not a valid choice' in r.get_data(as_text=True)


def test_section_visibility(app, admin):
    store(
        app, Project, title='Visibility test', slug='visibility',
        is_published=True,
    )

    assert admin.post('/admin/sections', data={'education': 'on'}).status_code == 302
    assert admin.get('/projects').status_code == 404
    assert admin.get('/projects/visibility').status_code == 404
    assert admin.get('/projects/visibility?preview=1').status_code == 200

    body = admin.get('/').get_data(as_text=True)
    assert 'id="research"' not in body and 'id="projects"' not in body

    sitemap = admin.get('/sitemap.xml').get_data(as_text=True)
    assert '/projects/visibility' not in sitemap


def test_contact_validation_and_save(app, client):
    assert client.post('/contact', data=message_data(email='not-email')).status_code == 200
    assert client.post('/contact', data=message_data(message='short')).status_code == 200
    assert client.post('/contact', data=message_data(consent='')).status_code == 200

    with app.app_context():
        assert db.session.scalar(
            db.select(db.func.count()).select_from(ContactMessage)
        ) == 0

    r = client.post('/contact', data=message_data(), follow_redirects=True)
    assert r.status_code == 200
    assert 'No email delivery is claimed' in r.get_data(as_text=True)

    with app.app_context():
        msg = db.session.scalar(db.select(ContactMessage))
        assert msg.delivery_status == 'saved'


def test_honeypot(client, app):
    assert client.post('/contact', data=message_data(website='spam')).status_code == 400

    with app.app_context():
        assert db.session.scalar(
            db.select(db.func.count()).select_from(ContactMessage)
        ) == 0


def test_message_xss_and_management(app, admin):
    mid = store(
        app,
        ContactMessage,
        name='<script>alert(1)</script>',
        email='user@example.com',
        subject='Example',
        message='<img src=x onerror=alert(1)>',
    )

    body = admin.get('/admin/messages').get_data(as_text=True)
    assert '&lt;script&gt;' in body and '<script>alert(1)' not in body
    assert '&lt;img src=x onerror=' in body
    assert admin.post(f'/admin/messages/{mid}/read').status_code == 302

    with app.app_context():
        assert db.session.get(ContactMessage, mid).is_read

    assert admin.post(f'/admin/messages/{mid}/delete').status_code == 302


def test_email_provider_failure_keeps_message(app, client, monkeypatch):
    app.config.update(
        MAIL_API_KEY='test',
        MAIL_FROM='from@example.com',
        MAIL_TO='to@example.com',
    )

    def failure(*args, **kwargs):
        raise OSError('mock unavailable')

    monkeypatch.setattr('app.public.routes.urlopen', failure)
    r = client.post('/contact', data=message_data(), follow_redirects=True)
    assert 'No email delivery is claimed' in r.get_data(as_text=True)

    with app.app_context():
        assert db.session.scalar(db.select(ContactMessage)).delivery_status == 'failed'


def test_email_provider_acceptance(app, client, monkeypatch):
    app.config.update(
        MAIL_API_KEY='test',
        MAIL_FROM='from@example.com',
        MAIL_TO='to@example.com',
    )

    class Accepted:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        'app.public.routes.urlopen',
        lambda *args, **kwargs: Accepted(),
    )
    r = client.post('/contact', data=message_data(), follow_redirects=True)
    assert 'accepted by the provider' in r.get_data(as_text=True)

    with app.app_context():
        assert db.session.scalar(db.select(ContactMessage)).delivery_status == 'provider_accepted'


def test_csrf_protection(app, client):
    app.config['WTF_CSRF_ENABLED'] = True
    assert client.post('/contact', data=message_data()).status_code == 400
    assert client.post(
        '/admin/login',
        data={'email': 'admin@example.com', 'password': 'test-only-password-12345'},
    ).status_code == 400

    body = client.get('/contact').get_data(as_text=True)
    token = re.search(
        r'name="csrf_token" type="hidden" value="([^"]+)"',
        body,
    ).group(1)

    assert client.post(
        '/contact',
        data=message_data(csrf_token=token),
    ).status_code == 302


def test_login_rate_limiting(app, client):
    app.config['TEST_RATE_LIMIT'] = True

    for _ in range(5):
        assert client.post(
            '/admin/login',
            data={'email': 'admin@example.com', 'password': 'bad'},
        ).status_code == 200

    assert client.post(
        '/admin/login',
        data={'email': 'admin@example.com', 'password': 'bad'},
    ).status_code == 429


def test_contact_rate_limiting(app, client):
    app.config['TEST_RATE_LIMIT'] = True

    for _ in range(5):
        assert client.post('/contact', data=message_data()).status_code == 302

    assert client.post('/contact', data=message_data()).status_code == 429


def make_png():
    out = BytesIO()
    Image.new('RGB', (100, 100), 'teal').save(out, format='PNG')
    out.seek(0)
    return out


def test_upload_processing_access_and_delete(app, admin):
    r = admin.post(
        '/admin/assets',
        data={
            'file': (make_png(), 'photo.png'),
            'kind': 'image',
            'alt_text': 'Test-only profile image',
        },
        content_type='multipart/form-data',
    )
    assert r.status_code == 302, r.get_data(as_text=True)

    with app.app_context():
        a = db.session.scalar(db.select(UploadedAsset))
        aid = a.id
        assert a.mime_type == 'image/webp' and not a.is_public
        assert a.data.startswith(b'RIFF')

        p = db.session.get(Profile, 1)
        p.photo_id = aid
        db.session.commit()

    guest = app.test_client(use_cookies=False)

    with guest:
        response = guest.get('/assets/' + str(aid))
        assert response.status_code == 404

    assert admin.get('/assets/' + str(aid)).status_code == 200
    assert admin.post(f'/admin/assets/{aid}/visibility').status_code == 302
    assert guest.get('/assets/' + str(aid)).status_code == 200
    assert admin.post(f'/admin/assets/{aid}/delete').status_code == 302

    with app.app_context():
        assert db.session.get(Profile, 1).photo_id is None


def test_invalid_file_rejected(app, admin):
    cases = [
        ('bad.svg', b'<svg onload=alert(1)>', 'image'),
        ('bad.pdf', b'not-a-pdf', 'cv'),
        ('bad.pdf', b'%PDF-1.4 /JavaScript test %%EOF', 'cv'),
    ]

    for name, raw, kind in cases:
        r = admin.post(
            '/admin/assets',
            data={
                'file': (BytesIO(raw), name),
                'kind': kind,
                'alt_text': 'Unsafe fixture',
            },
            content_type='multipart/form-data',
        )
        assert r.status_code == 200

    with app.app_context():
        assert db.session.scalar(
            db.select(db.func.count()).select_from(UploadedAsset)
        ) == 0


def test_file_size_limit(app, admin):
    app.config['MAX_ASSET_BYTES'] = 10
    r = admin.post(
        '/admin/assets',
        data={
            'file': (make_png(), 'large.png'),
            'kind': 'image',
            'alt_text': 'Fixture',
        },
        content_type='multipart/form-data',
    )
    assert 'larger than 8 MB' in r.get_data(as_text=True)


def test_public_cv(app, client):
    raw = b'%PDF-1.4\n1 0 obj <<>> endobj\n%%EOF'
    aid = store(
        app,
        UploadedAsset,
        filename='cv.pdf',
        mime_type='application/pdf',
        kind='cv',
        alt_text='Test fixture CV',
        data=raw,
        size=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(),
        is_public=True,
    )

    with app.app_context():
        p = db.session.get(Profile, 1)
        p.cv_id = aid
        db.session.commit()

    assert client.get('/cv').status_code == 200
    result = client.get('/cv/download')
    assert result.status_code == 200 and result.data == raw
    assert 'Aanchal-Singh-Academic-CV.pdf' in result.headers['Content-Disposition']
    assert 'Download CV' in client.get('/').get_data(as_text=True)


def test_health_dependency_failure(app, client, monkeypatch):
    assert client.get('/health').json == {'status': 'healthy'}

    def fail(*args, **kwargs):
        raise OperationalError('SELECT 1', {}, Exception('mock-down'))

    monkeypatch.setattr(db.session, 'execute', fail)
    result = client.get('/health')
    assert result.status_code == 503 and result.json['status'] == 'unhealthy'


def test_seeding_idempotent(app):
    with app.app_context():
        p = db.session.get(Profile, 1)
        p.biography = 'Owner edited biography'
        db.session.commit()

    runner = app.test_cli_runner()
    assert runner.invoke(args=['seed']).exit_code == 0

    with app.app_context():
        assert db.session.get(Profile, 1).biography == 'Owner edited biography'
        assert db.session.scalar(
            db.select(db.func.count()).select_from(Education)
        ) == 1
        assert db.session.scalar(
            db.select(db.func.count()).select_from(ResearchInterest)
        ) == 2


def test_security_headers_and_canonical(client):
    r = client.get('/')
    assert r.headers['X-Content-Type-Options'] == 'nosniff'
    assert "object-src 'none'" in r.headers['Content-Security-Policy']
    assert 'https://portfolio.example/' in r.get_data(as_text=True)
    assert '<loc>https://portfolio.example/projects</loc>' in client.get('/sitemap.xml').get_data(as_text=True)
    assert client.get('/robots.txt').get_data(as_text=True) == 'User-agent: *\nDisallow: /\n'


def test_pagination_and_search(app, client):
    for i in range(12):
        store(
            app, Project,
            title=f'Biology entry {i:02d}',
            slug=f'entry-{i}',
            is_published=True,
            category='Biotechnology',
        )

    body = client.get('/projects').get_data(as_text=True)
    assert 'Page 1 of 2' in body and '/projects?page=2' in body
    assert '/notes?page=2' not in body

    body = client.get('/projects?q=entry+11').get_data(as_text=True)
    assert 'Biology entry 11' in body and 'Biology entry 01' not in body
    assert 'Biology entry' not in client.get('/projects?q=%25').get_data(as_text=True)
    assert client.get('/projects?page=-1').status_code == 200


def test_safe_markdown(app, client):
    store(
        app,
        BlogPost,
        title='Test-only note',
        slug='test-note',
        is_published=True,
        publication_date=date.today(),
        content=(
            '## Heading\n\n```python\nprint("example")\n```\n\n'
            '[Safe citation](https://example.com)\n\n'
            '<script>alert(1)</script>\n\n'
            '[Bad](javascript:alert(1))'
        ),
    )

    body = client.get('/notes/test-note').get_data(as_text=True)
    assert '<h2>Heading</h2>' in body and 'language-python' in body
    assert 'href="https://example.com"' in body
    assert '<script>alert(1)' not in body and 'href="javascript:' not in body


def test_prune_private_data(app):
    with app.app_context():
        db.session.add(
            ContactMessage(
                name='Old',
                email='old@example.com',
                subject='Old enquiry',
                message='A prior message',
                created_at=datetime.now(timezone.utc) - timedelta(days=91),
            )
        )
        db.session.add(
            ThrottleBucket(key='expired', count=1, expires_at=1)
        )
        db.session.commit()

    result = app.test_cli_runner().invoke(args=['prune-private-data'])
    assert result.exit_code == 0

    with app.app_context():
        assert db.session.scalar(
            db.select(db.func.count()).select_from(ContactMessage)
        ) == 0
        assert db.session.get(ThrottleBucket, 'expired') is None


def test_create_admin_cli(app):
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=[
            'create-admin',
            '--email', 'new@example.com',
            '--password', 'new-test-only-pass-123',
        ]
    )
    assert result.exit_code == 0, result.output

    with app.app_context():
        user = db.session.scalar(
            db.select(AdminUser).where(
                AdminUser.email == 'new@example.com'
            )
        )
        assert user.password_hash != 'new-test-only-pass-123'
        assert user.check_password('new-test-only-pass-123')

    assert runner.invoke(
        args=[
            'create-admin',
            '--email', 'new@example.com',
            '--password', 'short',
        ]
    ).exit_code != 0


def test_environment_guards(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.delenv('SECRET_KEY', raising=False)

    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        create_app()

    monkeypatch.setenv('SECRET_KEY', 'a' * 40)
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///never-production.db')

    with pytest.raises(RuntimeError, match='PostgreSQL'):
        create_app()

    monkeypatch.setenv('DATABASE_URL', 'postgres://user:pass@localhost/unused')
    monkeypatch.setenv('BASE_URL', 'http://insecure.example')

    with pytest.raises(RuntimeError, match='BASE_URL'):
        create_app()

    monkeypatch.setenv('BASE_URL', 'https://portfolio.example')
    application = create_app()

    assert application.config['SESSION_COOKIE_SECURE']
    assert application.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql+psycopg://')


def test_production_https_redirect_and_host_guard(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('SECRET_KEY', 'a' * 40)
    monkeypatch.setenv('DATABASE_URL', 'postgres://user:pass@localhost/unused')
    monkeypatch.setenv('BASE_URL', 'https://portfolio.example')

    app = create_app()
    c = app.test_client()

    r = c.get('/health', base_url='http://portfolio.example')
    assert r.status_code == 308
    assert r.location == 'https://portfolio.example/health'
    assert c.get('/health', base_url='https://evil.example').status_code == 400


def test_migrations_on_clean_sqlite(tmp_path):
    uri = 'sqlite:///' + str(tmp_path / 'migration-test.db')
    app = create_app({
        'APP_ENV': 'testing',
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': uri,
        'WTF_CSRF_ENABLED': False,
    })

    runner = app.test_cli_runner()
    r = runner.invoke(args=['db', 'upgrade'])
    assert r.exit_code == 0, r.output
    assert runner.invoke(args=['seed']).exit_code == 0
    assert app.test_client().get('/health').status_code == 200

    r = runner.invoke(args=['db', 'upgrade'])
    assert r.exit_code == 0
    assert runner.invoke(args=['seed']).exit_code == 0

    with app.app_context():
        db.session.remove()
        db.engine.dispose()
