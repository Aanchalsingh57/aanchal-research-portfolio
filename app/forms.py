
import re
from urllib.parse import urlsplit

from flask import request
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import (
    StringField,
    TextAreaField,
    PasswordField,
    BooleanField,
    IntegerField,
    DateField,
    SelectField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    InputRequired,
    Optional,
    Length,
    Email,
    NumberRange,
    ValidationError,
)

from .extensions import db
from .models import UploadedAsset, Project, ResearchInterest
from .catalog import CATALOG


def safe_url(form, field):
    if not field.data:
        return

    value = field.data

    try:
        parts = urlsplit(value)
    except ValueError:
        raise ValidationError("Enter a valid HTTP(S) URL.")

    if (
        parts.scheme not in ("https", "http")
        or not parts.hostname
        or parts.username
        or parts.password
        or any(c.isspace() or ord(c) < 32 for c in value)
    ):
        raise ValidationError(
            "Use a complete http:// or https:// URL without credentials."
        )


def slug_check(form, field):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", field.data or ""):
        raise ValidationError(
            "Use lowercase letters, numbers and single hyphens."
        )


def static_path_check(form, field):
    """Allow paths relative to app/static/, not arbitrary filesystem paths."""
    value = (field.data or "").strip()

    if not value:
        return

    if (
        value.startswith("/")
        or "\\" in value
        or ":" in value
        or any(ord(char) < 32 for char in value)
    ):
        raise ValidationError(
            "Enter a relative path inside app/static/, without a leading slash."
        )

    parts = value.split("/")

    if any(part in ("", ".", "..") for part in parts):
        raise ValidationError(
            "Use a valid relative path, for example images/aanchal-profile.jpg."
        )

    if not value.startswith(("images/", "files/")):
        raise ValidationError(
            "The path must begin with images/ or files/."
        )

    if not re.fullmatch(r"[A-Za-z0-9._/-]+", value):
        raise ValidationError(
            "Use only letters, numbers, dots, underscores, hyphens and slashes."
        )

    if field.name == "cv_path":
        if not value.startswith("files/") or not value.lower().endswith(".pdf"):
            raise ValidationError(
                "The CV path must point to a PDF inside app/static/files/."
            )


class LoginForm(FlaskForm):
    email = StringField(
        "Administrator email",
        validators=[DataRequired(), Email(), Length(max=254)],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(max=256)],
    )
    submit = SubmitField("Sign in securely")


class ActionForm(FlaskForm):
    submit = SubmitField("Confirm")


class ContactForm(FlaskForm):
    name = StringField(
        "Your name",
        validators=[DataRequired(), Length(min=2, max=120)],
    )
    email = StringField(
        "Email address",
        validators=[DataRequired(), Email(), Length(max=254)],
    )
    subject = StringField(
        "Subject",
        validators=[DataRequired(), Length(min=3, max=180)],
    )
    message = TextAreaField(
        "Message",
        validators=[DataRequired(), Length(min=20, max=5000)],
    )
    website = StringField(
        "Leave this field empty",
        validators=[Length(max=200)],
    )
    consent = BooleanField(
        "I agree to the privacy notice and storage of my message.",
        validators=[DataRequired()],
    )
    submit = SubmitField("Send message")


class AssetForm(FlaskForm):
    file = FileField(
        "File (PNG, JPEG, WebP, or PDF; 8 MB maximum)",
        validators=[FileRequired()],
    )
    kind = SelectField(
        "Asset type",
        choices=[
            ("image", "Profile / research image"),
            ("cv", "Academic CV (PDF)"),
            ("document", "Poster / document (PDF)"),
        ],
    )
    alt_text = StringField(
        "Image description / document label",
        validators=[DataRequired(), Length(max=300)],
    )
    is_public = BooleanField("Allow public access to this file")
    submit = SubmitField("Upload to database")


def editor_form(kind, obj=None):
    model, _, spec = CATALOG[kind]
    fields = {}

    path_labels = {
        "photo_path": "Profile image path (inside app/static/)",
        "cv_path": "CV PDF path (inside app/static/)",
        "image_path": "Project image path (inside app/static/)",
        "cover_path": "Research note cover path (inside app/static/)",
    }

    for token in spec.split():
        name, typ = token.split(":")
        required = typ.endswith("*")
        typ = typ.rstrip("*")

        label = path_labels.get(
            name,
            name.replace("_id", "").replace("_", " ").capitalize(),
        )

        column = model.__table__.columns[name]
        maxlen = getattr(column.type, "length", None) or 30000

        validators = [
            DataRequired() if required else Optional()
        ]

        if typ in ("S", "T", "U", "E", "L", "Y"):
            validators.append(Length(max=maxlen))

        if typ == "U":
            validators.append(safe_url)

        if typ == "E":
            validators.append(Email())

        if typ == "L":
            validators.append(slug_check)

        if name in ("photo_path", "cv_path", "image_path", "cover_path"):
            validators.append(static_path_check)

        if typ == "Y":
            def year_validator(form, field):
                if field.data and not re.fullmatch(r"[0-9]{4}", field.data):
                    raise ValidationError("Use a four-digit year.")

            validators.append(year_validator)

        if typ == "B":
            field = BooleanField(label)

        elif typ == "T":
            field = TextAreaField(label, validators=validators)

        elif typ == "I":
            field = IntegerField(
                label,
                default=0,
                validators=[
                    InputRequired(),
                    NumberRange(min=0, max=100000),
                ],
            )

        elif typ == "D":
            field = DateField(label, validators=[Optional()])

        
        elif typ == "R":
            if name in ("photo_id", "cv_id", "image_id", "cover_id"):
                asset_kind = "cv" if name == "cv_id" else "image"

                rows = db.session.scalars(
                    db.select(UploadedAsset)
                    .where(UploadedAsset.kind == asset_kind)
                    .order_by(UploadedAsset.id.desc())
                ).all()

                choices = [(0, "None")] + [
                    (
                        row.id,
                        row.filename
                        + (" · private" if not row.is_public else ""),
                    )
                    for row in rows
                ]
            else:
                related = Project if name == "project_id" else ResearchInterest

                rows = db.session.scalars(
                    db.select(related).order_by(related.id)
                ).all()

                choices = [(0, "None")] + [
                    (row.id, row.title) for row in rows
                ]

            field = SelectField(
                label,
                choices=choices,
                coerce=int,
                validators=[Optional()],
            )


        elif typ in ("K", "SC", "PS", "OS"):
            opts = {
                "K": [
                    ("research", "Research interest"),
                    ("aiml", "AI/ML topic"),
                ],
                "SC": [
                    (value, value)
                    for value in [
                        "Biotechnology and Laboratory",
                        "Computational and Data",
                        "AI/ML",
                        "Bioinformatics",
                        "Tools and Platforms",
                    ]
                ],
                "PS": [
                    (value, value)
                    for value in [
                        "",
                        "Planned",
                        "Ongoing",
                        "Completed",
                        "Archived",
                    ]
                ],
                "OS": [
                    (value, value)
                    for value in [
                        "",
                        "Published",
                        "Accepted",
                        "Under Review",
                        "Preprint",
                        "In Preparation",
                    ]
                ],
            }[typ]

            field = SelectField(
                label,
                choices=opts,
                validators=validators,
            )

        else:
            field = StringField(label, validators=validators)

        fields[name] = field

    fields["submit"] = SubmitField("Save changes")

    cls = type("EditorForm", (FlaskForm,), fields)
    form = cls(obj=obj)

    # Legacy relationship fields should render the explicit None option.
    if obj and request.method == "GET":
        for name in fields:
            if name.endswith("_id") and getattr(obj, name, None) is None:
                getattr(form, name).data = 0

    return form
