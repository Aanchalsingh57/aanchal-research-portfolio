from datetime import datetime,timezone
import sqlite3
import click
from flask import Flask, g, render_template, request, redirect, url_for
from flask_login import current_user
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash
from config import configuration
from .extensions import db,login_manager,migrate,csrf

@event.listens_for(Engine,'connect')
def sqlite_foreign_keys(connection,record):
    if isinstance(connection,sqlite3.Connection):connection.execute('PRAGMA foreign_keys=ON')

def create_app(overrides=None):
    app=Flask(__name__)
    app.config.update(configuration(overrides))
    @app.before_request
    def clear_stale_login_user():
        # Prevent a cached user from leaking across reused app contexts.
        g.pop("_login_user", None)
    if app.config['APP_ENV']=='production':
        # Render is one trusted edge proxy. Do not use this setting behind an arbitrary proxy chain.
        app.wsgi_app=ProxyFix(app.wsgi_app,x_for=1,x_proto=1,x_host=0,x_port=0)
    db.init_app(app);login_manager.init_app(app);migrate.init_app(app,db);csrf.init_app(app)
    login_manager.login_view='admin.login';login_manager.session_protection='strong'
    from .models import AdminUser,Profile,SocialLink,SectionSetting
    @login_manager.user_loader
    def load_user(uid):
        try:return db.session.get(AdminUser,int(uid))
        except (ValueError,TypeError):return None
    from .public.routes import public
    from .admin.routes import admin
    app.register_blueprint(public);app.register_blueprint(admin)
    from .catalog import CATALOG,SECTIONS
    from .forms import ActionForm
    @app.context_processor
    def common():
        # Error and health responses remain available even if the DB is unavailable.
        if request.endpoint=='public.health' or getattr(request,'minimal_context',False):return {}
        profile=db.session.get(Profile,1)
        from pathlib import Path

        cv_available = bool(
            profile
            and (
                (
                    profile.cv
                    and profile.cv.kind == "cv"
                    and profile.cv.is_public
                    and profile.cv.mime_type == "application/pdf"
                )
                or (
                    profile.cv_path
                    and profile.cv_path.lower().endswith(".pdf")
                    and (Path(app.static_folder) / profile.cv_path).is_file()
                )
            )
        )
        links=db.session.scalars(db.select(SocialLink).where(SocialLink.is_published.is_(True)).order_by(SocialLink.sort_order,SocialLink.id)).all()
        settings={x.key:x.enabled for x in db.session.scalars(db.select(SectionSetting))}
        return dict(profile=profile,cv_available=cv_available,links=links,sections={k:settings.get(k,True) for k in SECTIONS},
            current_year=datetime.now(timezone.utc).year,action_form=ActionForm(),catalog=CATALOG,
            canonical_url=(app.config['BASE_URL']+request.path) if app.config['BASE_URL'] else None,
            site_indexable=app.config['SITE_INDEXABLE'])
    @app.before_request
    def force_https():
        if app.config['APP_ENV']=='production' and not request.is_secure:
            return redirect(app.config['BASE_URL']+request.path+('?' + request.query_string.decode('ascii',errors='ignore') if request.query_string else ''),code=308)
    @app.after_request
    def secure_headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
        response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        if app.config['APP_ENV']=='production':response.headers['Strict-Transport-Security']='max-age=31536000'
        if request.path.startswith('/admin') or request.args.get('preview')=='1':
            response.headers['Cache-Control']='no-store';response.headers['X-Robots-Tag']='noindex, nofollow'
        elif not app.config['SITE_INDEXABLE']:response.headers['X-Robots-Tag']='noindex, nofollow'
        return response
    def error_page(error):
        db.session.rollback();request.minimal_context=True
        code=getattr(error,'code',500)
        if code==500:app.logger.error('Unhandled application error; request failed.')
        response=app.make_response((render_template('errors/error.html',code=code),code))
        if code==429:response.headers['Retry-After']=str(getattr(request,'rate_retry_after',900))
        return response
    for code in (400,403,404,413,429,500,503):app.register_error_handler(code,error_page)
    from flask_wtf.csrf import CSRFError
    app.register_error_handler(CSRFError,error_page)
    from markdown_it import MarkdownIt
    from markupsafe import Markup
    markdown=MarkdownIt('commonmark',{'html':False}).disable('image')
    @app.template_filter('safe_markdown')
    def safe_markdown(value):return Markup(markdown.render(value or ''))
    register_cli(app)
    return app

def register_cli(app):
    from .models import Profile,Education,ResearchInterest,SectionSetting,AdminUser,ContactMessage,ThrottleBucket
    from .catalog import SECTIONS
    @app.cli.command('seed')
    def seed():
        """Insert only verified starting content; never overwrite existing records."""
        is_new_profile=db.session.get(Profile,1) is None
        if is_new_profile:
            db.session.add(Profile(id=1,name='Aanchal Singh',degree='M.Tech Biotechnology',
                institution='National Institute of Technology Jalandhar (NIT Jalandhar)',
                headline='Biotechnology Research | AI/ML in Life Sciences',
                tagline='Exploring the intersection of biotechnology, data, and intelligent scientific discovery.',
                introduction='I am an M.Tech Biotechnology student at the National Institute of Technology Jalandhar, interested in biotechnology research and the application of artificial intelligence and machine learning to biological problems.',
                biography='My academic direction is biotechnology research, with an interest in computational approaches to biological problems. I aspire to pursue a PhD in biotechnology or a closely related research area.'))
        if is_new_profile and not db.session.scalar(db.select(Education.id).limit(1)):
            db.session.add(Education(degree='M.Tech Biotechnology',institution='National Institute of Technology Jalandhar (NIT Jalandhar)',is_current=True,is_published=True))
        if is_new_profile and not db.session.scalar(db.select(ResearchInterest.id).limit(1)):
            db.session.add_all([ResearchInterest(title='Biotechnology research',description='An academic interest in investigating biological questions through biotechnology research.',is_published=True,sort_order=0),ResearchInterest(title='AI/ML in biotechnology',description='An interest in how artificial intelligence and machine learning can support the study of biological problems.',is_published=True,sort_order=1)])
        existing=set(db.session.scalars(db.select(SectionSetting.key)))
        for key in SECTIONS:
            if key not in existing:db.session.add(SectionSetting(key=key,enabled=True))
        db.session.commit();click.echo('Verified starting content initialized. Existing content was not overwritten.')
    @app.cli.command('create-admin')
    @click.option('--email',prompt=True)
    @click.password_option(confirmation_prompt=True)
    def create_admin(email,password):
        from email_validator import validate_email,EmailNotValidError
        try:email=validate_email(email,check_deliverability=False).normalized.lower()
        except EmailNotValidError as exc:raise click.ClickException(str(exc))
        if len(password)<14 or len(password)>256:raise click.ClickException('Use a password between 14 and 256 characters.')
        if db.session.scalar(db.select(AdminUser).where(AdminUser.email==email)):raise click.ClickException('Administrator already exists. Use reset-admin-password.')
        user=AdminUser(email=email);user.set_password(password);db.session.add(user);db.session.commit();click.echo('Administrator created. No public registration route exists.')
    @app.cli.command('reset-admin-password')
    @click.option('--email',prompt=True)
    @click.password_option(confirmation_prompt=True)
    def reset_admin(email,password):
        user=db.session.scalar(db.select(AdminUser).where(AdminUser.email==email.strip().lower()))
        if not user:raise click.ClickException('Administrator not found.')
        if not 14<=len(password)<=256:raise click.ClickException('Use 14–256 characters.')
        user.set_password(password);db.session.commit();click.echo('Password changed. Restart workers to clear active sessions if necessary; rotate SECRET_KEY to invalidate all sessions.')
    @app.cli.command('prune-private-data')
    def prune_private_data():
        import time
        from datetime import timedelta
        cutoff=datetime.now(timezone.utc)-timedelta(days=app.config['CONTACT_RETENTION_DAYS'])
        messages=db.session.execute(db.delete(ContactMessage).where(ContactMessage.created_at<cutoff)).rowcount
        db.session.execute(db.delete(ThrottleBucket).where(ThrottleBucket.expires_at<int(time.time())))
        db.session.commit();click.echo(f'Deleted {messages} expired contact messages and expired throttle counters.')
