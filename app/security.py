import hashlib,hmac,time
from flask import request,current_app,abort
from sqlalchemy import delete
from .extensions import db
from .models import ThrottleBucket

def rate_limit(scope,maximum,seconds):
    if current_app.config.get('TESTING') and not current_app.config.get('TEST_RATE_LIMIT'):return
    now=int(time.time());window=now//seconds
    ident=hmac.new(current_app.secret_key.encode(),(request.remote_addr or 'unknown').encode(),hashlib.sha256).hexdigest()
    key=f'{scope}:{window}:{ident}'
    values={'key':key,'count':1,'expires_at':(window+1)*seconds}
    dialect=db.engine.dialect.name
    if dialect=='postgresql':
        from sqlalchemy.dialects.postgresql import insert
    elif dialect=='sqlite':
        from sqlalchemy.dialects.sqlite import insert
    else:abort(503)
    stmt=insert(ThrottleBucket).values(**values)
    stmt=stmt.on_conflict_do_update(index_elements=['key'],set_={'count':ThrottleBucket.count+1}).returning(ThrottleBucket.count)
    count=db.session.execute(stmt).scalar_one()
    db.session.commit()
    if count>maximum:
        request.rate_retry_after=(window+1)*seconds-now
        abort(429)

def is_admin(user):return user.is_authenticated and user.role=='admin'
