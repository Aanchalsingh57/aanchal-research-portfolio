import os
from datetime import timedelta
from urllib.parse import urlsplit

def configuration(overrides=None):
    env=os.getenv('APP_ENV','development')
    production=env=='production'
    url=os.getenv('DATABASE_URL','sqlite:///portfolio-dev.db')
    if url.startswith('postgres://'): url='postgresql+psycopg://'+url[len('postgres://'):]
    elif url.startswith('postgresql://'): url='postgresql+psycopg://'+url[len('postgresql://'):]
    secret=os.getenv('SECRET_KEY')
    base=os.getenv('BASE_URL','').rstrip('/')
    cfg=dict(SECRET_KEY=secret or 'development-only-do-not-use-in-production',APP_ENV=env,
        SQLALCHEMY_DATABASE_URI=url,SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={'pool_pre_ping':True,'pool_recycle':300},
        MAX_CONTENT_LENGTH=9*1024*1024,MAX_ASSET_BYTES=8*1024*1024,MAX_ASSET_TOTAL_BYTES=64*1024*1024,
        SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=production,
        REMEMBER_COOKIE_HTTPONLY=True,REMEMBER_COOKIE_SECURE=production,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=2),WTF_CSRF_TIME_LIMIT=7200,
        BASE_URL=base,TRUSTED_HOSTS=(list(dict.fromkeys(filter(None, [urlsplit(base).hostname,"localhost" if not production else None,"127.0.0.1" if not production else None,os.getenv("RENDER_EXTERNAL_HOSTNAME"),]))) or None),
        MAIL_API_KEY=os.getenv('MAIL_API_KEY',''),MAIL_FROM=os.getenv('MAIL_FROM',''),
        MAIL_TO=os.getenv('MAIL_TO',''),CONTACT_RETENTION_DAYS=90,
        SITE_INDEXABLE=os.getenv('SITE_INDEXABLE','false').lower()=='true',TESTING=False)
    if overrides: cfg.update(overrides)
    if cfg['APP_ENV']=='production':
        if not cfg['SECRET_KEY'] or len(cfg['SECRET_KEY'])<32 or cfg['SECRET_KEY'].startswith('development-'):
            raise RuntimeError('Production requires a strong SECRET_KEY of at least 32 characters.')
        if not cfg['SQLALCHEMY_DATABASE_URI'].startswith('postgresql+psycopg://'):
            raise RuntimeError('Production requires a PostgreSQL DATABASE_URL.')
        parsed=urlsplit(cfg['BASE_URL'])
        if parsed.scheme!='https' or not parsed.hostname or parsed.path not in ('','/'):
            raise RuntimeError('Production requires BASE_URL=https://your-domain without a path.')
    return cfg
