
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db


def now():
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), default=now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now, nullable=False)


class AdminUser(UserMixin, TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='admin')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='scrypt')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class UploadedAsset(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    mime_type = db.Column(db.String(80), nullable=False)
    kind = db.Column(db.String(20), nullable=False)
    alt_text = db.Column(db.String(300), default='')
    data = db.deferred(db.Column(db.LargeBinary, nullable=False))
    size = db.Column(db.Integer, nullable=False)
    sha256 = db.Column(db.String(64), nullable=False)
    is_public = db.Column(db.Boolean, nullable=False, default=False, index=True)


class Profile(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    headline = db.Column(db.String(250), default='')
    degree = db.Column(db.String(200), default='')
    institution = db.Column(db.String(250), default='')
    tagline = db.Column(db.String(300), default='')
    introduction = db.Column(db.Text, default='')
    biography = db.Column(db.Text, default='')
    specialization = db.Column(db.String(250), default='')
    current_research = db.Column(db.Text, default='')
    supervisor = db.Column(db.String(200), default='')
    laboratory = db.Column(db.String(200), default='')
    expected_graduation = db.Column(db.String(30), default='')
    email = db.Column(db.String(254), default='')
    collaboration = db.Column(db.Text, default='')
    cv_summary = db.Column(db.Text, default='')

    # Paths to public files committed to the repository.
    # Examples: images/aanchal-profile.jpg
    photo_path = db.Column(db.String(500), nullable=False, default='')
    cv_path = db.Column(db.String(500), nullable=False, default='')

    # Existing database-backed assets retained for compatibility.
    photo_id = db.Column(db.Integer, db.ForeignKey('uploaded_asset.id', ondelete='SET NULL'))
    cv_id = db.Column(db.Integer, db.ForeignKey('uploaded_asset.id', ondelete='SET NULL'))
    photo = db.relationship('UploadedAsset', foreign_keys=[photo_id])
    cv = db.relationship('UploadedAsset', foreign_keys=[cv_id])


class OrderedMixin:
    sort_order = db.Column(db.Integer, nullable=False, default=0, index=True)
    is_published = db.Column(db.Boolean, nullable=False, default=False, index=True)


class ResearchInterest(TimestampMixin, OrderedMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    motivation = db.Column(db.Text, default='')
    methods = db.Column(db.Text, default='')
    biological_problem = db.Column(db.Text, default='')
    example_questions = db.Column(db.Text, default='')
    literature = db.Column(db.Text, default='')
    kind = db.Column(db.String(20), nullable=False, default='research')


class Project(TimestampMixin, OrderedMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(220), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    summary = db.Column(db.Text, default='')
    category = db.Column(db.String(80), default='')
    status = db.Column(db.String(60), default='')
    start_date = db.Column(db.String(30), default='')
    end_date = db.Column(db.String(30), default='')
    institution = db.Column(db.String(250), default='')
    laboratory = db.Column(db.String(250), default='')
    background = db.Column(db.Text, default='')
    research_question = db.Column(db.Text, default='')
    motivation = db.Column(db.Text, default='')
    objectives = db.Column(db.Text, default='')
    materials = db.Column(db.Text, default='')
    methods = db.Column(db.Text, default='')
    workflow = db.Column(db.Text, default='')
    tools = db.Column(db.Text, default='')
    results = db.Column(db.Text, default='')
    discussion = db.Column(db.Text, default='')
    limitations = db.Column(db.Text, default='')
    future_scope = db.Column(db.Text, default='')
    references = db.Column(db.Text, default='')
    dataset_source = db.Column(db.String(500), default='')
    dataset_size = db.Column(db.String(120), default='')
    preprocessing = db.Column(db.Text, default='')
    feature_engineering = db.Column(db.Text, default='')
    algorithms = db.Column(db.Text, default='')
    training = db.Column(db.Text, default='')
    metrics = db.Column(db.Text, default='')
    validation = db.Column(db.Text, default='')
    reproducibility = db.Column(db.Text, default='')
    repository_url = db.Column(db.String(500), default='')
    paper_url = db.Column(db.String(500), default='')
    poster_url = db.Column(db.String(500), default='')
    is_featured = db.Column(db.Boolean, nullable=False, default=False)
    interest_id = db.Column(
        db.Integer,
        db.ForeignKey('research_interest.id', ondelete='SET NULL'),
        index=True
    )
    interest = db.relationship('ResearchInterest', backref='projects')

    # Repository-relative path, e.g. images/projects/pneumonia.jpg
    image_path = db.Column(db.String(500), nullable=False, default='')

    # Existing uploaded-asset relationship retained for compatibility.
    image_id = db.Column(db.Integer, db.ForeignKey('uploaded_asset.id', ondelete='SET NULL'))
    image = db.relationship('UploadedAsset')


class Skill(TimestampMixin, OrderedMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default='')
    proficiency = db.Column(db.String(120), default='')
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='SET NULL'), index=True)
    project = db.relationship('Project', backref='skills')


class Education(TimestampMixin, OrderedMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    degree = db.Column(db.String(200), nullable=False)
    institution = db.Column(db.String(250), nullable=False)
    department = db.Column(db.String(200), default='')
    start_year = db.Column(db.String(30), default='')
    end_year = db.Column(db.String(30), default='')
    specialization = db.Column(db.String(250), default='')
    score = db.Column(db.String(80), default='')
    coursework = db.Column(db.Text, default='')
    thesis = db.Column(db.Text, default='')
    achievements = db.Column(db.Text, default='')
    is_current = db.Column(db.Boolean, default=False, nullable=False)


class Experience(TimestampMixin, OrderedMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(200), nullable=False)
    organization = db.Column(db.String(250), nullable=False)
    department = db.Column(db.String(200), default='')
    supervisor = db.Column(db.String(200), default='')
    start_date = db.Column(db.String(30), default='')
    end_date = db.Column(db.String(30), default='')
    description = db.Column(db.Text, default='')
    responsibilities = db.Column(db.Text, default='')
    techniques = db.Column(db.Text, default='')
    outcomes = db.Column(db.Text, default='')
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='SET NULL'), index=True)
    project = db.relationship('Project', backref='experiences')


class Publication(TimestampMixin, OrderedMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    authors = db.Column(db.Text, default='')
    year = db.Column(db.String(10), default='')
    venue = db.Column(db.String(250), default='')
    doi = db.Column(db.String(250), default='')
    status = db.Column(db.String(80), default='')
    output_type = db.Column(db.String(100), default='')
    abstract = db.Column(db.Text, default='')
    publisher_url = db.Column(db.String(500), default='')
    pdf_url = db.Column(db.String(500), default='')
    citation = db.Column(db.Text, default='')
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='SET NULL'), index=True)
    project = db.relationship('Project', backref='publications')
    interest_id = db.Column(db.Integer, db.ForeignKey('research_interest.id', ondelete='SET NULL'), index=True)
    interest = db.relationship('ResearchInterest', backref='publications')


class Achievement(TimestampMixin, OrderedMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(220), nullable=False)
    date = db.Column(db.String(40), default='')
    organization = db.Column(db.String(250), default='')
    category = db.Column(db.String(100), default='')
    description = db.Column(db.Text, default='')
    evidence_url = db.Column(db.String(500), default='')


class BlogPost(TimestampMixin, OrderedMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(220), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    summary = db.Column(db.Text, default='')
    content = db.Column(db.Text, default='')
    category = db.Column(db.String(100), default='')
    publication_date = db.Column(db.Date)
    tags = db.Column(db.String(400), default='')
    references = db.Column(db.Text, default='')

    # Repository-relative path, e.g. images/notes/research-note.jpg
    cover_path = db.Column(db.String(500), nullable=False, default='')

    # Existing uploaded-asset relationship retained for compatibility.
    cover_id = db.Column(db.Integer, db.ForeignKey('uploaded_asset.id', ondelete='SET NULL'))
    cover = db.relationship('UploadedAsset')

    @property
    def reading_time(self):
        return max(1, len((self.content or '').split()) // 200)


class SocialLink(TimestampMixin, OrderedMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)


class SectionSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True)


class ContactMessage(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    subject = db.Column(db.String(180), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    delivery_status = db.Column(db.String(30), nullable=False, default='saved')


class ThrottleBucket(db.Model):
    key = db.Column(db.String(100), primary_key=True)
    count = db.Column(db.Integer, nullable=False, default=1)
    expires_at = db.Column(db.Integer, nullable=False, index=True)
