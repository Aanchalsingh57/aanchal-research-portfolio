
from io import BytesIO
import hashlib

from PIL import Image, UnidentifiedImageError
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    current_app,
    session,
)
from flask_login import (
    login_user,
    logout_user,
    current_user,
)
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models import *
from ..forms import LoginForm, ActionForm, AssetForm, editor_form
from ..catalog import CATALOG, SECTIONS
from ..security import is_admin, rate_limit


admin = Blueprint("admin", __name__, url_prefix="/admin")

DUMMY_HASH = generate_password_hash(
    "unusable-not-a-real-password",
    method="scrypt",
)


@admin.before_request
def protect():
    if request.endpoint == "admin.login":
        return

    if not current_user.is_authenticated:
        return current_app.login_manager.unauthorized()

    if not is_admin(current_user):
        abort(403)


@admin.route("/login", methods=["GET", "POST"])
def login():
    if is_admin(current_user):
        return redirect(url_for("admin.dashboard"))

    form = LoginForm()

    if request.method == "POST":
        rate_limit("login", 5, 900)

    if form.validate_on_submit():
        user = db.session.scalar(
            db.select(AdminUser).where(
                AdminUser.email == form.email.data.strip().lower()
            )
        )

        valid = check_password_hash(
            user.password_hash if user else DUMMY_HASH,
            form.password.data,
        )

        if user and valid and user.role == "admin":
            session.clear()
            login_user(user, remember=False, fresh=True)
            session.permanent = True
            return redirect(url_for("admin.dashboard"))

        flash("Invalid administrator credentials.", "error")

    return render_template("login.html", form=form)


@admin.post("/logout")
def logout():
    form = ActionForm()

    if not form.validate_on_submit():
        abort(400)

    logout_user()
    session.clear()

    return redirect(url_for("public.index"))


@admin.get("/")
def dashboard():
    stats = {
        key: db.session.scalar(
            db.select(db.func.count()).select_from(model)
        )
        for key, (model, _, _) in CATALOG.items()
        if key != "profile"
    }

    profile = db.session.get(Profile, 1)

    checklist = [
        (
            "Profile photograph",
            bool(profile and profile.photo_path),
            "admin.profile",
        ),
        (
            "Academic biography",
            bool(profile and profile.biography),
            "admin.profile",
        ),
        (
            "Undergraduate education",
            db.session.scalar(
                db.select(db.func.count()).select_from(Education)
            ) > 1,
            "admin.content",
            {"kind": "education"},
        ),
        (
            "Current research topic",
            bool(profile and profile.current_research),
            "admin.profile",
        ),
        (
            "Confirmed research interests",
            stats["interests"] > 0,
            "admin.content",
            {"kind": "interests"},
        ),
        (
            "Technical skills",
            bool(
                db.session.scalar(
                    db.select(Skill.id)
                    .where(
                        Skill.category != "Biotechnology and Laboratory"
                    )
                    .limit(1)
                )
            ),
            "admin.content",
            {"kind": "skills"},
        ),
        (
            "Laboratory skills",
            bool(
                db.session.scalar(
                    db.select(Skill.id)
                    .where(
                        Skill.category == "Biotechnology and Laboratory"
                    )
                    .limit(1)
                )
            ),
            "admin.content",
            {"kind": "skills"},
        ),
        (
            "Research experience",
            stats["experience"] > 0,
            "admin.content",
            {"kind": "experience"},
        ),
        (
            "Projects",
            stats["projects"] > 0,
            "admin.content",
            {"kind": "projects"},
        ),
        (
            "Academic CV",
            bool(profile and profile.cv_path),
            "admin.profile",
        ),
        (
            "Professional links",
            stats["links"] > 0,
            "admin.content",
            {"kind": "links"},
        ),
        (
            "Publications, when available",
            stats["publications"] > 0,
            "admin.content",
            {"kind": "publications"},
        ),
    ]

    unread = db.session.scalar(
        db.select(db.func.count())
        .select_from(ContactMessage)
        .where(ContactMessage.is_read.is_(False))
    )

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        checklist=checklist,
        unread=unread,
    )


@admin.route("/profile", methods=["GET", "POST"])
def profile():
    obj = db.session.get(Profile, 1)

    if not obj:
        abort(503)

    form = editor_form("profile", obj)

    if form.validate_on_submit():
        apply_form("profile", obj, form)
        db.session.commit()

        flash("Profile updated.", "success")
        return redirect(url_for("admin.profile"))

    return render_template(
        "admin/editor.html",
        form=form,
        kind="profile",
        item=obj,
        title="Edit profile",
    )


def get_catalog(kind):
    if kind not in CATALOG or kind == "profile":
        abort(404)

    return CATALOG[kind]


def apply_form(kind, obj, form):
    for token in CATALOG[kind][2].split():
        name, typ = token.split(":")
        value = getattr(form, name).data

        if isinstance(value, str):
            value = value.strip()

        if typ.rstrip("*") == "R":
            value = value or None

        setattr(obj, name, value)


@admin.get("/content/<kind>")
def content(kind):
    model, label, _ = get_catalog(kind)

    pagination = db.paginate(
        db.select(model).order_by(
            model.sort_order,
            model.id.desc(),
        ),
        page=max(1, request.args.get("page", 1, type=int) or 1),
        per_page=20,
        error_out=False,
    )

    return render_template(
        "admin/content.html",
        kind=kind,
        label=label,
        pagination=pagination,
        items=pagination.items,
    )


@admin.route("/content/<kind>/new", methods=["GET", "POST"])
@admin.route("/content/<kind>/<int:item_id>/edit", methods=["GET", "POST"])
def edit(kind, item_id=None):
    model, label, _ = get_catalog(kind)

    obj = db.session.get(model, item_id) if item_id else model()

    if obj is None:
        abort(404)

    form = editor_form(kind, obj if item_id else None)

    if form.validate_on_submit():
        apply_form(kind, obj, form)

        if kind == "notes" and obj.is_published and not obj.publication_date:
            form.publication_date.errors.append(
                "Set the actual publication date before publishing."
            )
        else:
            try:
                db.session.add(obj)
                db.session.commit()

                flash(
                    "Content saved. Only published entries appear publicly.",
                    "success",
                )
                return redirect(
                    url_for("admin.content", kind=kind)
                )

            except IntegrityError:
                db.session.rollback()
                flash(
                    "That URL slug is already in use. Choose a unique slug.",
                    "error",
                )

    return render_template(
        "admin/editor.html",
        form=form,
        kind=kind,
        item=obj,
        title=("Edit " if item_id else "Add ") + label.lower(),
    )


@admin.post("/content/<kind>/<int:item_id>/delete")
def delete(kind, item_id):
    model, _, _ = get_catalog(kind)

    if not ActionForm().validate_on_submit():
        abort(400)

    obj = db.session.get(model, item_id)

    if not obj:
        abort(404)

    db.session.delete(obj)
    db.session.commit()

    flash("Entry deleted.", "success")
    return redirect(url_for("admin.content", kind=kind))


@admin.route("/sections", methods=["GET", "POST"])
def sections():
    form = ActionForm()

    if form.validate_on_submit():
        for key in SECTIONS:
            row = db.session.scalar(
                db.select(SectionSetting).where(
                    SectionSetting.key == key
                )
            )

            if row is None:
                row = SectionSetting(key=key)
                db.session.add(row)

            row.enabled = request.form.get(key) == "on"

        db.session.commit()

        flash(
            "Section visibility updated. Disabled sections are also "
            "unavailable at their public URLs.",
            "success",
        )
        return redirect(url_for("admin.sections"))

    rows = {
        row.key: row.enabled
        for row in db.session.scalars(
            db.select(SectionSetting)
        )
    }

    return render_template(
        "admin/sections.html",
        form=form,
        section_keys=SECTIONS,
        settings=rows,
    )


@admin.route("/assets", methods=["GET", "POST"])
def assets():
    form = AssetForm()

    if form.validate_on_submit():
        file = form.file.data
        raw = file.stream.read(
            current_app.config["MAX_ASSET_BYTES"] + 1
        )
        error = None
        name = secure_filename(file.filename or "")

        if not raw or len(raw) > current_app.config["MAX_ASSET_BYTES"]:
            error = "File is empty or larger than 8 MB."

        elif form.kind.data == "image":
            try:
                Image.MAX_IMAGE_PIXELS = 20_000_000

                with Image.open(
                    BytesIO(raw),
                    formats=("PNG", "JPEG", "WEBP"),
                ) as image:
                    if (
                        image.format not in ("PNG", "JPEG", "WEBP")
                        or image.width * image.height > 20_000_000
                    ):
                        raise ValueError("Unsupported or oversized image.")

                    image.verify()

                with Image.open(
                    BytesIO(raw),
                    formats=("PNG", "JPEG", "WEBP"),
                ) as image:
                    image.thumbnail((1800, 1800))
                    out = BytesIO()
                    image.convert("RGB").save(
                        out,
                        format="WEBP",
                        quality=86,
                    )
                    raw = out.getvalue()
                    mime = "image/webp"
                    name = (
                        (name.rsplit(".", 1)[0] or "image") + ".webp"
                    )

            except (
                UnidentifiedImageError,
                OSError,
                ValueError,
                Image.DecompressionBombError,
                Image.DecompressionBombWarning,
            ):
                error = (
                    "Upload a valid PNG, JPEG, or WebP image "
                    "under 20 megapixels."
                )

        else:
            if (
                not name.lower().endswith(".pdf")
                or not raw.startswith(b"%PDF-")
                or b"%%EOF" not in raw[-2048:]
            ):
                error = "Upload a valid PDF document."

            elif any(
                marker in raw
                for marker in [
                    b"/JavaScript",
                    b"/JS ",
                    b"/Launch",
                    b"/EmbeddedFile",
                    b"/OpenAction",
                ]
            ):
                error = (
                    "Active content and embedded files are not "
                    "permitted in PDFs."
                )

            mime = "application/pdf"

        used = db.session.scalar(
            db.select(
                db.func.coalesce(db.func.sum(UploadedAsset.size), 0)
            )
        )

        if (
            not error
            and used + len(raw)
            > current_app.config["MAX_ASSET_TOTAL_BYTES"]
        ):
            error = (
                "The asset storage quota (64 MB) has been reached. "
                "Remove unused assets first."
            )

        if error:
            flash(error, "error")

        else:
            asset = UploadedAsset(
                filename=name[:200],
                kind=form.kind.data,
                mime_type=mime,
                data=raw,
                size=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(),
                alt_text=form.alt_text.data.strip(),
                is_public=form.is_public.data,
            )

            db.session.add(asset)
            db.session.commit()

            flash(
                "File stored in the configured database. "
                "Repository-based static files can instead be referenced "
                "from the profile and content editors.",
                "success",
            )
            return redirect(url_for("admin.assets"))

    rows = db.session.scalars(
        db.select(UploadedAsset).order_by(UploadedAsset.id.desc())
    ).all()

    return render_template(
        "admin/assets.html",
        form=form,
        assets=rows,
    )


@admin.post("/assets/<int:asset_id>/<action>")
def asset_action(asset_id, action):
    if not ActionForm().validate_on_submit():
        abort(400)

    asset = db.session.get(UploadedAsset, asset_id)

    if not asset:
        abort(404)

    if action == "delete":
        db.session.delete(asset)

    elif action == "visibility":
        asset.is_public = not asset.is_public

    else:
        abort(404)

    db.session.commit()

    flash(
        "Asset updated. Public caches can retain a previously public "
        "file for up to one hour.",
        "success",
    )

    return redirect(url_for("admin.assets"))


@admin.get("/messages")
def messages():
    pagination = db.paginate(
        db.select(ContactMessage).order_by(
            ContactMessage.created_at.desc()
        ),
        page=max(1, request.args.get("page", 1, type=int) or 1),
        per_page=20,
        error_out=False,
    )

    return render_template(
        "admin/messages.html",
        pagination=pagination,
        messages=pagination.items,
    )


@admin.post("/messages/<int:item_id>/<action>")
def message_action(item_id, action):
    if not ActionForm().validate_on_submit():
        abort(400)

    obj = db.session.get(ContactMessage, item_id)

    if not obj:
        abort(404)

    if action == "delete":
        db.session.delete(obj)

    elif action == "read":
        obj.is_read = True

    else:
        abort(404)

    db.session.commit()

    flash("Message updated.", "success")
    return redirect(url_for("admin.messages"))
