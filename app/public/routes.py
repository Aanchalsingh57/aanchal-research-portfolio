from flask import request, session
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit
import json
from urllib.request import Request, urlopen

from flask import (
    Blueprint,
    render_template,
    request,
    abort,
    current_app,
    url_for,
    redirect,
    flash,
    send_file,
    Response,
)
from flask_login import current_user
from sqlalchemy import text
from ..extensions import db
from ..models import *
from ..forms import ContactForm
from ..security import is_admin, rate_limit

public = Blueprint("public", __name__)


def visible(model):
    return (
        db.select(model)
        .where(model.is_published.is_(True))
        .order_by(model.sort_order, model.id)
    )


def enabled(key):
    row = db.session.scalar(
        db.select(SectionSetting).where(SectionSetting.key == key)
    )
    return row is None or row.enabled


def static_file_exists(relative_path):
    """Check that a relative path resolves to a file under app/static/."""
    if not relative_path:
        return False

    static_root = Path(current_app.static_folder).resolve()
    candidate = (static_root / relative_path).resolve()

    try:
        candidate.relative_to(static_root)
    except ValueError:
        return False

    return candidate.is_file()


def detail(model, slug, section):
    preview = (
        is_admin(current_user)
        and request.args.get("preview") == "1"
    )

    if not enabled(section) and not preview:
        abort(404)

    stmt = db.select(model).where(model.slug == slug)

    if not preview:
        stmt = stmt.where(model.is_published.is_(True))

    obj = db.session.scalar(stmt)

    if not obj:
        abort(404)

    return obj, preview


@public.get("/")
def index():
    profile = db.session.get(Profile, 1)

    interests = db.session.scalars(visible(ResearchInterest)).all()
    projects = db.session.scalars(
        visible(Project)
        .where(Project.is_featured.is_(True))
        .limit(3)
    ).all()
    education = db.session.scalars(visible(Education)).all()
    skills = db.session.scalars(visible(Skill)).all()
    experiences = db.session.scalars(visible(Experience)).all()
    achievements = db.session.scalars(visible(Achievement)).all()
    publications = db.session.scalars(
        visible(Publication).limit(3)
    ).all()
    notes = db.session.scalars(visible(BlogPost).limit(3)).all()

    return render_template(
        "index.html",
        profile=profile,
        interests=[x for x in interests if x.kind == "research"],
        topics=[x for x in interests if x.kind == "aiml"],
        projects=projects,
        education=education,
        skills=skills,
        experiences=experiences,
        achievements=achievements,
        publications=publications,
        notes=notes,
    )


@public.get("/about")
def about():
    if not enabled("about"):
        abort(404)

    return render_template(
        "about.html",
        education=db.session.scalars(visible(Education)).all(),
    )


@public.get("/research/<int:interest_id>")
def interest(interest_id):
    obj = db.session.get(ResearchInterest, interest_id)

    if (
        not obj
        or not obj.is_published
        or not enabled("interests" if obj.kind == "research" else "aiml")
    ):
        abort(404)

    projects = (
        db.session.scalars(
            visible(Project).where(Project.interest_id == obj.id)
        ).all()
        if enabled("projects")
        else []
    )

    publications = (
        db.session.scalars(
            visible(Publication).where(Publication.interest_id == obj.id)
        ).all()
        if enabled("publications")
        else []
    )

    return render_template(
        "interest.html",
        item=obj,
        projects=projects,
        publications=publications,
    )


@public.get("/projects", defaults={"kind": "projects"})
@public.get("/publications", defaults={"kind": "publications"})
@public.get("/notes", defaults={"kind": "notes"})
def listing(kind):
    if not enabled(kind):
        abort(404)

    model = {
        "projects": Project,
        "publications": Publication,
        "notes": BlogPost,
    }[kind]

    q = request.args.get("q", "").strip()[:100]
    category = request.args.get("category", "")[:100]

    stmt = visible(model)

    if q:
        escaped = (
            q.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        stmt = stmt.where(
            model.title.ilike("%" + escaped + "%", escape="\\")
        )

    filter_col = (
        Publication.status
        if model == Publication
        else model.category
    )

    if category:
        stmt = stmt.where(filter_col == category)

    categories = db.session.scalars(
        db.select(filter_col)
        .where(
            model.is_published.is_(True),
            filter_col != "",
        )
        .distinct()
        .order_by(filter_col)
    ).all()

    page = max(1, request.args.get("page", 1, type=int) or 1)

    pagination = db.paginate(
        stmt,
        page=page,
        per_page=9,
        max_per_page=9,
        error_out=False,
    )

    return render_template(
        "listing.html",
        kind=kind,
        items=pagination.items,
        pagination=pagination,
        categories=categories,
        q=q,
        category=category,
    )


@public.get("/projects/<slug>")
def project_detail(slug):
    obj, preview = detail(Project, slug, "projects")

    fields = [
        ("background", "Background"),
        ("research_question", "Research question"),
        ("motivation", "Scientific motivation"),
        ("objectives", "Objectives"),
        ("materials", "Materials / biological material"),
        ("methods", "Materials and methods"),
        ("workflow", "Computational / experimental workflow"),
        ("tools", "Tools and technologies"),
        ("dataset_size", "Dataset size"),
        ("preprocessing", "Data preprocessing"),
        ("feature_engineering", "Feature engineering / representation learning"),
        ("algorithms", "Algorithms / architectures"),
        ("training", "Training methodology"),
        ("metrics", "Evaluation metrics"),
        ("validation", "Validation strategy"),
        ("results", "Results"),
        ("discussion", "Discussion"),
        ("limitations", "Limitations"),
        ("future_scope", "Future scope"),
        ("reproducibility", "Reproducibility"),
        ("references", "References"),
    ]

    return render_template(
        "detail.html",
        kind="projects",
        item=obj,
        preview=preview,
        fields=fields,
    )


@public.get("/publications/<slug>")
def publication_detail(slug):
    obj, preview = detail(Publication, slug, "publications")

    return render_template(
        "detail.html",
        kind="publications",
        item=obj,
        preview=preview,
        fields=[
            ("abstract", "Abstract"),
            ("citation", "Citation"),
        ],
    )


@public.get("/notes/<slug>")
def blog_detail(slug):
    obj, preview = detail(BlogPost, slug, "notes")

    return render_template(
        "detail.html",
        kind="notes",
        item=obj,
        preview=preview,
        fields=[
            ("content", "Research note"),
            ("references", "References"),
        ],
    )


@public.route("/contact", methods=["GET", "POST"])
def contact():
    if not enabled("contact"):
        abort(404)

    form = ContactForm()

    if request.method == "POST":
        rate_limit("contact", 5, 3600)

    if form.validate_on_submit():
        if form.website.data:
            abort(400)

        msg = ContactMessage(
            name=form.name.data.strip(),
            email=form.email.data.strip(),
            subject=form.subject.data.strip(),
            message=form.message.data.strip(),
        )

        db.session.add(msg)
        db.session.commit()

        delivered = False
        cfg = current_app.config

        if cfg["MAIL_API_KEY"] and cfg["MAIL_FROM"] and cfg["MAIL_TO"]:
            body = json.dumps({
                "from": cfg["MAIL_FROM"],
                "to": [cfg["MAIL_TO"]],
                "subject": "Portfolio enquiry: " + msg.subject,
                "reply_to": msg.email,
                "text": (
                    f"From: {msg.name} <{msg.email}>\n\n"
                    f"{msg.message}"
                ),
            }).encode()

            req = Request(
                "https://api.resend.com/emails",
                data=body,
                headers={
                    "Authorization": "Bearer " + cfg["MAIL_API_KEY"],
                    "Content-Type": "application/json",
                    "User-Agent": "ResearchPortfolio/1.0",
                },
                method="POST",
            )

            try:
                with urlopen(req, timeout=8) as response:
                    delivered = response.status == 200

                msg.delivery_status = (
                    "provider_accepted" if delivered else "failed"
                )

            except Exception:
                msg.delivery_status = "failed"
                current_app.logger.warning(
                    "Mail delivery failed; contact retained "
                    "in protected database."
                )

            db.session.commit()

        flash(
            "Your message was saved securely. An email notification "
            "was accepted by the provider."
            if delivered
            else "Your message was saved securely for Aanchal to review. "
                 "No email delivery is claimed.",
            "success",
        )

        return redirect(url_for("public.contact"))

    return render_template("contact.html", form=form)


@public.get("/privacy")
def privacy():
    return render_template(
        "privacy.html",
        retention=current_app.config["CONTACT_RETENTION_DAYS"],
    )



@public.get("/cv")
def cv():
    if not enabled("cv"):
        abort(404)

    profile = db.session.get(Profile, 1)
    if not profile:
        abort(404)

    asset = db.session.get(UploadedAsset, profile.cv_id) if profile.cv_id else None

    if asset and asset.kind == "cv" and asset.is_public and asset.mime_type == "application/pdf":
        return render_template(
            "cv.html",
            asset=asset,
            cv_url=url_for("public.asset", asset_id=asset.id),
            cv_download_url=url_for("public.cv_download"),
        )

    if (
        not profile.cv_path
        or not static_file_exists(profile.cv_path)
        or not profile.cv_path.lower().endswith(".pdf")
    ):
        abort(404)

    return render_template(
        "cv.html",
        asset=None,
        cv_url=url_for("static", filename=profile.cv_path),
        cv_download_url=url_for("public.cv_download"),
    )


@public.get("/cv/download")
def cv_download():
    if not enabled("cv"):
        abort(404)

    profile = db.session.get(Profile, 1)
    if not profile:
        abort(404)

    asset = db.session.get(UploadedAsset, profile.cv_id) if profile.cv_id else None

    if asset and asset.kind == "cv" and asset.is_public and asset.mime_type == "application/pdf":
        return send_file(
            BytesIO(asset.data),
            mimetype="application/pdf",
            as_attachment=True,
            download_name="Aanchal-Singh-Academic-CV.pdf",
            max_age=0,
        )

    if (
        not profile.cv_path
        or not static_file_exists(profile.cv_path)
        or not profile.cv_path.lower().endswith(".pdf")
    ):
        abort(404)

    return send_file(
        Path(current_app.static_folder) / profile.cv_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="Aanchal-Singh-Academic-CV.pdf",
        max_age=0,
    )



@public.get("/assets/<int:asset_id>")
def asset(asset_id):
    asset = db.session.get(UploadedAsset, asset_id)

    if asset is None:
        abort(404)

    if not asset.is_public:
        # Private assets must only be accessible to an authenticated admin.
        if not current_user.is_authenticated or not is_admin(current_user):
            abort(404)

    response = send_file(
        BytesIO(asset.data),
        mimetype=asset.mime_type,
        download_name=asset.filename,
        as_attachment=asset.mime_type == "application/pdf",
        etag=asset.sha256,
        max_age=3600 if asset.is_public else 0,
    )

    if not asset.is_public:
        response.headers["Cache-Control"] = "private, no-store"

    return response


@public.get("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))

        if not db.session.get(Profile, 1):
            return {
                "status": "unhealthy",
                "reason": "initialization_required",
            }, 503

        return {"status": "healthy"}, 200

    except Exception:
        db.session.rollback()
        return {
            "status": "unhealthy",
            "reason": "database_unavailable",
        }, 503


@public.get("/robots.txt")
def robots():
    base = current_app.config["BASE_URL"]

    data = (
        "User-agent: *\n"
        "Disallow: /admin\n"
        "Disallow: /assets/\n"
    )

    if not current_app.config["SITE_INDEXABLE"]:
        data = "User-agent: *\nDisallow: /\n"
    elif base:
        data += "Sitemap: " + base + "/sitemap.xml\n"

    return Response(data, mimetype="text/plain")


@public.get("/sitemap.xml")
def sitemap():
    from xml.sax.saxutils import escape

    base = current_app.config["BASE_URL"]

    if not base:
        return Response(
            "Set BASE_URL to enable the sitemap.",
            503,
            mimetype="text/plain",
        )

    paths = ["/", "/privacy"]

    if enabled("about"):
        paths.append("/about")

    if enabled("contact"):
        paths.append("/contact")

    for key, model in [
        ("projects", Project),
        ("publications", Publication),
        ("notes", BlogPost),
    ]:
        if enabled(key):
            paths.append("/" + key)
            paths.extend(
                "/" + key + "/" + item.slug
                for item in db.session.scalars(visible(model))
            )

    for obj in db.session.scalars(visible(ResearchInterest)):
        section = "aiml" if obj.kind == "aiml" else "interests"

        if enabled(section):
            paths.append("/research/" + str(obj.id))

    profile = db.session.get(Profile, 1)

    if (
        enabled("cv")
        and profile
        and profile.cv_path
        and static_file_exists(profile.cv_path)
        and profile.cv_path.lower().endswith(".pdf")
    ):
        paths.append("/cv")

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    )

    xml += "".join(
        "<url><loc>" + escape(base + path) + "</loc></url>"
        for path in paths
    )

    xml += "</urlset>"

    return Response(xml, mimetype="application/xml")
