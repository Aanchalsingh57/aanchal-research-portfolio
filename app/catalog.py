
from .models import (
    Profile,
    ResearchInterest,
    Project,
    Skill,
    Education,
    Experience,
    Publication,
    Achievement,
    BlogPost,
    SocialLink,
)

# Explicit allowlists prevent mass assignment of IDs, hashes, or asset bytes.
#
# Field spec:
# S  = short text
# T  = multiline text
# U  = safe HTTP(S) URL
# E  = email
# I  = nonnegative order
# B  = checkbox
# D  = date
# R  = relationship dropdown
# L  = slug
# K, PS, SC, Y, OS = custom choice fields
#
# Image and CV files are now referenced by paths inside app/static/.
# Examples:
#   images/aanchal-profile.jpg
#   files/aanchal-cv.pdf
#   images/projects/pneumonia-detection.jpg
#   images/notes/research-note.jpg

CATALOG = {
    "profile": (
        Profile,
        "Profile",
        "name:S* headline:S degree:S institution:S tagline:S "
        "introduction:T biography:T specialization:S current_research:T "
        "supervisor:S laboratory:S expected_graduation:S email:E "
        "collaboration:T cv_summary:T photo_path:S cv_path:S",
    ),

    "interests": (
        ResearchInterest,
        "Research interests",
        "title:S* description:T motivation:T methods:T "
        "biological_problem:T example_questions:T literature:T "
        "kind:K sort_order:I is_published:B",
    ),

    "projects": (
        Project,
        "Projects",
        "title:S* slug:L* summary:T category:S status:PS "
        "start_date:S end_date:S institution:S laboratory:S "
        "background:T research_question:T motivation:T objectives:T "
        "materials:T methods:T workflow:T tools:T results:T discussion:T "
        "limitations:T future_scope:T references:T dataset_source:U "
        "dataset_size:S preprocessing:T feature_engineering:T algorithms:T "
        "training:T metrics:T validation:T reproducibility:T repository_url:U "
        "paper_url:U poster_url:U interest_id:R image_path:S "
        "is_featured:B sort_order:I is_published:B",
    ),

    "skills": (
        Skill,
        "Skills",
        "name:S* category:SC description:T proficiency:S "
        "project_id:R sort_order:I is_published:B",
    ),

    "education": (
        Education,
        "Education",
        "degree:S* institution:S* department:S start_year:S end_year:S "
        "specialization:S score:S coursework:T thesis:T achievements:T "
        "is_current:B sort_order:I is_published:B",
    ),

    "experience": (
        Experience,
        "Experience",
        "role:S* organization:S* department:S supervisor:S "
        "start_date:S end_date:S description:T responsibilities:T "
        "techniques:T outcomes:T project_id:R sort_order:I is_published:B",
    ),

    "publications": (
        Publication,
        "Publications",
        "title:S* slug:L* authors:T year:Y venue:S doi:S status:OS "
        "output_type:S abstract:T publisher_url:U pdf_url:U citation:T "
        "project_id:R interest_id:R sort_order:I is_published:B",
    ),

    "achievements": (
        Achievement,
        "Achievements",
        "title:S* date:S organization:S category:S description:T "
        "evidence_url:U sort_order:I is_published:B",
    ),

    "notes": (
        BlogPost,
        "Research notes",
        "title:S* slug:L* summary:T content:T category:S "
        "publication_date:D tags:S references:T cover_path:S "
        "sort_order:I is_published:B",
    ),

    "links": (
        SocialLink,
        "Professional links",
        "label:S* url:U* sort_order:I is_published:B",
    ),
}

SECTIONS = [
    "about",
    "interests",
    "projects",
    "aiml",
    "skills",
    "experience",
    "education",
    "publications",
    "achievements",
    "cv",
    "notes",
    "contact",
]
