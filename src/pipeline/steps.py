from src.pipeline.context import PipelineContext
from src.tools.file_store import register_artifact, save_json_artifact
from src.utils.logger import get_logger


logger = get_logger(__name__)


def _save_step_artifact(context: PipelineContext, key: str, filename: str, data: object) -> PipelineContext:
    filepath = save_json_artifact(data, filename)
    logger.info("Saved artifact %s to %s", key, filepath)
    return register_artifact(context, key, filepath)


def slugify(value: str) -> str:
    return "-".join(value.lower().replace("/", " ").replace(",", " ").split())


def build_page(slug: str, page_type: str, title_hint: str, purpose: str) -> dict[str, str]:
    return {
        "slug": slugify(slug),
        "page_type": page_type,
        "title_hint": title_hint,
        "purpose": purpose,
    }


def build_base_pages(niche: str, city: str, site_type: str, include_blog: bool) -> list[dict[str, str]]:
    pages = [
        build_page("home", "home", f"{niche.title()} in {city}", "Main landing page for the local offer."),
        build_page("services", "services", f"{niche.title()} for {city}", "Overview of core services."),
        build_page("about", "about", f"About Our {niche.title()} Team in {city}", "Trust and company background."),
        build_page("contact", "contact", f"Contact {niche.title()} in {city}", "Lead capture and contact details."),
    ]

    if site_type == "local_service_site":
        pages.extend(
            [
                build_page(
                    "service-areas",
                    "service_areas",
                    f"Service Areas for {niche.title()} in {city}",
                    "Coverage overview for nearby areas.",
                ),
                build_page(
                    "faq",
                    "faq",
                    f"{niche.title()} FAQ for {city}",
                    "Answers to common customer questions.",
                ),
            ]
        )

    if include_blog:
        pages.append(
            build_page(
                "blog",
                "blog",
                f"{niche.title()} Blog for {city}",
                "Educational content and supporting SEO articles.",
            )
        )

    return pages


def build_service_pages(niche: str, city: str) -> list[dict[str, str]]:
    service_names = [
        "Emergency Service",
        "Installation",
        "Repair",
    ]
    return [
        build_page(
            service_name,
            "service_detail",
            f"{service_name} {niche.title()} in {city}",
            f"Dedicated landing page for {service_name.lower()} leads.",
        )
        for service_name in service_names
    ]


def build_location_pages(niche: str, city: str) -> list[dict[str, str]]:
    nearby_areas = [
        f"{city} Downtown",
        f"North {city}",
        f"South {city}",
    ]
    return [
        build_page(
            area_name,
            "location_page",
            f"{niche.title()} in {area_name}",
            "Localized landing page for geographic relevance.",
        )
        for area_name in nearby_areas
    ]


def get_template_sections() -> dict[str, list[str]]:
    return {
        "home": ["hero", "services_overview", "trust_signals", "faq_preview", "contact_cta"],
        "services": ["services_list", "process", "faq_preview", "contact_cta"],
        "service_detail": ["hero", "service_description", "benefits", "faq_preview", "contact_cta"],
        "location_page": ["hero", "local_relevance", "service_summary", "faq_preview", "contact_cta"],
        "about": ["company_story", "trust_signals", "team_or_values", "contact_cta"],
        "contact": ["contact_form", "contact_details", "service_area_summary"],
        "faq": ["faq_list", "contact_cta"],
        "blog": ["blog_index"],
        "service_areas": ["areas_list", "service_summary", "contact_cta"],
    }


def get_page_type_seo_notes(page_type: str) -> list[str]:
    seo_notes_map = {
        "home": ["primary local landing page"],
        "services": ["service overview / cluster support"],
        "service_detail": ["target service-intent keywords"],
        "location_page": ["target geo-modified keywords"],
        "faq": ["long-tail and objections"],
        "blog": ["informational support content"],
        "contact": ["trust and internal linking support"],
        "about": ["trust and internal linking support"],
        "service_areas": ["trust and internal linking support"],
    }
    return seo_notes_map.get(page_type, [])


def humanize_slug(slug: str) -> str:
    return slug.replace("-", " ").strip().title()


def dedupe_keywords(keywords: list[str]) -> list[str]:
    unique_keywords = []
    seen = set()

    for keyword in keywords:
        normalized = " ".join(keyword.split()).strip()
        if not normalized:
            continue
        if normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        unique_keywords.append(normalized)

    return unique_keywords


def build_keywords_for_page(page: dict[str, str], niche: str, city: str) -> dict[str, object] | None:
    page_type = page.get("page_type", "")
    page_slug = page.get("slug", "")
    niche_phrase = niche.strip()
    city_phrase = city.strip()

    if page_type == "home":
        keywords = [
            f"{niche_phrase} {city_phrase}",
            f"{niche_phrase} in {city_phrase}",
            f"best {niche_phrase} {city_phrase}",
        ]
        return {
            "cluster_name": "home_local",
            "intent": "transactional_local",
            "page_slug": page_slug,
            "keywords": dedupe_keywords(keywords),
        }

    if page_type == "services":
        keywords = [
            f"{niche_phrase} services {city_phrase}",
            f"{niche_phrase} company {city_phrase}",
            f"{niche_phrase} solutions {city_phrase}",
        ]
        return {
            "cluster_name": "services_overview",
            "intent": "commercial_investigation",
            "page_slug": page_slug,
            "keywords": dedupe_keywords(keywords),
        }

    if page_type == "service_detail":
        service_phrase = humanize_slug(page_slug).lower()
        keywords = [
            f"{service_phrase} {city_phrase}",
            f"{service_phrase} in {city_phrase}",
            f"{service_phrase} near me",
        ]
        return {
            "cluster_name": f"service_{page_slug}",
            "intent": "service_intent",
            "page_slug": page_slug,
            "keywords": dedupe_keywords(keywords),
        }

    if page_type == "location_page":
        location_phrase = humanize_slug(page_slug)
        keywords = [
            f"{niche_phrase} {location_phrase}",
            f"{niche_phrase} in {location_phrase}",
            f"best {niche_phrase} {location_phrase}",
        ]
        return {
            "cluster_name": f"location_{page_slug}",
            "intent": "geo_local",
            "page_slug": page_slug,
            "keywords": dedupe_keywords(keywords),
        }

    if page_type == "faq":
        keywords = [
            f"{niche_phrase} faq {city_phrase}",
            f"{niche_phrase} questions {city_phrase}",
            f"how to choose {niche_phrase} {city_phrase}",
        ]
        return {
            "cluster_name": "faq_questions",
            "intent": "informational",
            "page_slug": page_slug,
            "keywords": dedupe_keywords(keywords),
        }

    if page_type == "blog":
        keywords = [
            f"{niche_phrase} blog {city_phrase}",
            f"{niche_phrase} tips {city_phrase}",
            f"{niche_phrase} guide {city_phrase}",
        ]
        return {
            "cluster_name": "blog_support",
            "intent": "informational_support",
            "page_slug": page_slug,
            "keywords": dedupe_keywords(keywords),
        }

    if page_type == "service_areas":
        keywords = [
            f"{niche_phrase} service areas {city_phrase}",
            f"{niche_phrase} near {city_phrase}",
            f"{niche_phrase} coverage {city_phrase}",
        ]
        return {
            "cluster_name": "service_areas_support",
            "intent": "geo_support",
            "page_slug": page_slug,
            "keywords": dedupe_keywords(keywords),
        }

    return None


def count_total_keywords(clusters: list[dict[str, object]]) -> int:
    return sum(len(cluster.get("keywords", [])) for cluster in clusters)


def get_priority_tier(page_type: str) -> str:
    if page_type in {"home", "service_detail", "location_page"}:
        return "tier_1"
    if page_type in {"services", "faq", "service_areas"}:
        return "tier_2"
    return "tier_3"


def get_primary_goal(page_type: str) -> str:
    goals = {
        "home": "capture primary local demand",
        "service_detail": "capture service-intent demand",
        "location_page": "capture geo-modified demand",
        "services": "support service discovery",
        "faq": "support long-tail informational queries",
        "service_areas": "reinforce geographic relevance",
        "about": "trust and conversion support",
        "contact": "trust and conversion support",
        "blog": "informational support and topical breadth",
    }
    return goals.get(page_type, "support page goals")


def get_priority_reason(page_type: str, tier: str) -> str:
    reasons = {
        "home": "Tier 1 because it is the main local entry page for core demand.",
        "service_detail": "Tier 1 because service-intent pages target high-conversion queries.",
        "location_page": "Tier 1 because geo pages target localized demand directly.",
        "services": "Tier 2 because it supports discovery and internal linking to service pages.",
        "faq": "Tier 2 because it supports long-tail coverage and objection handling.",
        "service_areas": "Tier 2 because it strengthens geographic relevance across the site.",
        "about": "Tier 3 because it mainly supports trust rather than primary search capture.",
        "contact": "Tier 3 because it mainly supports conversion after discovery.",
        "blog": "Tier 3 because it supports topical breadth rather than core commercial demand.",
    }
    return reasons.get(page_type, f"{tier} based on deterministic page type rules.")


def get_target_cluster_names(page_slug: str, keyword_clusters: list[dict[str, object]]) -> list[str]:
    return [
        str(cluster.get("cluster_name", ""))
        for cluster in keyword_clusters
        if cluster.get("page_slug") == page_slug
    ]


def get_cluster_count(page_slug: str, keyword_clusters: list[dict[str, object]]) -> int:
    return sum(1 for cluster in keyword_clusters if cluster.get("page_slug") == page_slug)


def get_coverage_status(priority_tier: str, cluster_count: int) -> str:
    if cluster_count >= 1:
        return "covered"
    if priority_tier == "tier_1":
        return "missing"
    return "weak"


def get_coverage_notes(coverage_status: str) -> list[str]:
    if coverage_status == "covered":
        return ["Page has at least one mapped semantic cluster."]
    if coverage_status == "missing":
        return ["High-priority page has no mapped semantic cluster."]
    return ["Support page currently has no dedicated semantic coverage."]


def build_gap_recommendations(
    covered_count: int,
    weak_count: int,
    missing_count: int,
) -> list[str]:
    recommendations = []

    if missing_count > 0:
        recommendations.append(
            "Strengthen semantic coverage for high-priority pages before moving deeper into production."
        )

    if weak_count > 0:
        recommendations.append(
            "Expand support clusters for secondary and trust-building pages where useful."
        )

    if covered_count > 0 and missing_count == 0 and weak_count == 0:
        recommendations.append(
            "Semantic coverage is complete for this draft, so the project can move to content planning and build execution."
        )

    return recommendations


def collect_keywords_for_clusters(
    target_cluster_names: list[str],
    keyword_clusters: list[dict[str, object]],
) -> list[str]:
    keywords = []
    for cluster in keyword_clusters:
        if cluster.get("cluster_name") in target_cluster_names:
            keywords.extend(cluster.get("keywords", []))
    return dedupe_keywords(keywords)


def get_relevant_pain_groups(page_type: str, pain_groups: list[dict[str, object]]) -> list[str]:
    relevant_groups = []
    for group in pain_groups:
        if page_type in group.get("suggested_page_types", []):
            relevant_groups.append(str(group.get("group_name", "")))
    return relevant_groups


def get_build_priority(priority_tier: str, coverage_status: str) -> str:
    if priority_tier == "tier_1" and coverage_status in {"weak", "missing"}:
        return "urgent"
    if priority_tier == "tier_1" and coverage_status == "covered":
        return "high"
    if priority_tier == "tier_2":
        return "medium"
    return "low"


def get_execution_sort_key(page: dict[str, object]) -> tuple[int, str]:
    slug = str(page.get("slug", ""))
    page_type = str(page.get("page_type", ""))

    if slug == "home":
        return (0, slug)
    if slug == "services":
        return (1, slug)
    if slug == "about":
        return (2, slug)
    if slug == "contact":
        return (3, slug)
    if page_type == "service_detail":
        return (4, slug)
    if page_type == "location_page":
        return (5, slug)
    if slug == "faq":
        return (6, slug)
    if slug == "service-areas":
        return (7, slug)
    if slug == "blog":
        return (8, slug)
    return (9, slug)


def get_why_now(page: dict[str, object]) -> str:
    slug = str(page.get("slug", ""))
    page_type = str(page.get("page_type", ""))

    if slug == "home":
        return "Core entry page needed before supporting pages."
    if slug in {"services", "about", "contact"}:
        return "Supports trust and conversion."
    if page_type == "service_detail":
        return "High-priority revenue page."
    if page_type == "location_page":
        return "Expands high-intent local landing coverage."
    if slug in {"faq", "service-areas", "blog"}:
        return "Support content can be built after primary pages."
    return "Can be built after core pages are in place."


def get_depends_on(page: dict[str, object]) -> list[str]:
    slug = str(page.get("slug", ""))
    page_type = str(page.get("page_type", ""))

    if slug == "home":
        return []
    if slug == "services":
        return ["home"]
    if slug in {"about", "contact"}:
        return ["home"]
    if page_type == "service_detail":
        return ["services"]
    if page_type == "location_page":
        return ["home", "services"]
    if slug in {"faq", "service-areas"}:
        return ["services"]
    if slug == "blog":
        return ["home"]
    return ["home"]


def get_phase_summary(sorted_pages: list[dict[str, object]]) -> dict[str, list[str]]:
    foundation_pages = []
    money_pages = []
    support_pages = []
    later_pages = []

    for page in sorted_pages:
        slug = str(page.get("slug", ""))
        page_type = str(page.get("page_type", ""))
        priority_tier = str(page.get("priority_tier", ""))

        if slug in {"home", "services", "about", "contact"}:
            foundation_pages.append(slug)
        elif page_type in {"service_detail", "location_page"} or priority_tier == "tier_1":
            money_pages.append(slug)
        elif slug in {"faq", "service-areas"} or priority_tier == "tier_2":
            support_pages.append(slug)
        else:
            later_pages.append(slug)

    return {
        "foundation_pages": foundation_pages,
        "money_pages": money_pages,
        "support_pages": support_pages,
        "later_pages": later_pages,
    }


def normalize_page_type_list(page_types: list[str], available_page_types: set[str]) -> list[str]:
    return [page_type for page_type in page_types if page_type in available_page_types]


def count_total_pains(pain_groups: list[dict[str, object]]) -> int:
    return sum(len(group.get("pains", [])) for group in pain_groups)


def build_pain_groups_for_site_type(
    site_type: str,
    niche: str,
    city: str,
    available_page_types: set[str],
    tier_1_page_types: set[str],
) -> list[dict[str, object]]:
    niche_phrase = niche.strip()
    city_phrase = city.strip()

    if site_type == "local_service_site":
        groups = [
            {
                "group_name": "urgency_emergency",
                "audience_intent": f"Users in {city_phrase} who need {niche_phrase} quickly.",
                "pains": [
                    "need fast response",
                    "problem feels urgent",
                    "want to reach a provider immediately",
                ],
                "desired_outcomes": [
                    "get help quickly",
                    "reach the provider without delay",
                ],
                "suggested_page_types": ["home", "service_detail", "contact"],
            },
            {
                "group_name": "trust_credibility",
                "audience_intent": f"Users evaluating whether a {niche_phrase} provider in {city_phrase} is trustworthy.",
                "pains": [
                    "lack of trust in unknown company",
                    "uncertainty about service quality",
                    "fear of choosing the wrong provider",
                ],
                "desired_outcomes": [
                    "choose a reliable provider",
                    "feel confident before contacting the company",
                ],
                "suggested_page_types": ["about", "home"],
            },
            {
                "group_name": "pricing_transparency",
                "audience_intent": f"Users comparing costs and scope for {niche_phrase} in {city_phrase}.",
                "pains": [
                    "fear of overpaying",
                    "pricing is unclear",
                    "uncertainty about what is included",
                ],
                "desired_outcomes": [
                    "understand pricing",
                    "compare options with less friction",
                ],
                "suggested_page_types": ["services", "service_detail", "faq"],
            },
            {
                "group_name": "availability_service_area",
                "audience_intent": f"Users checking whether {niche_phrase} is available in their area around {city_phrase}.",
                "pains": [
                    "unclear service coverage",
                    "not sure whether provider serves the location",
                    "difficulty confirming availability",
                ],
                "desired_outcomes": [
                    "confirm service availability in city",
                    "know whether the provider covers the area",
                ],
                "suggested_page_types": ["service_areas", "location_page", "contact"],
            },
            {
                "group_name": "quality_reliability",
                "audience_intent": f"Users wanting dependable {niche_phrase} results in {city_phrase}.",
                "pains": [
                    "worry that the job will not be done properly",
                    "concern about repeat issues after service",
                    "uncertainty about provider reliability",
                ],
                "desired_outcomes": [
                    "reduce service risk",
                    "get dependable results",
                ],
                "suggested_page_types": ["home", "service_detail", "about"],
            },
            {
                "group_name": "decision_support",
                "audience_intent": f"Users who need help comparing and understanding {niche_phrase} options in {city_phrase}.",
                "pains": [
                    "difficulty choosing the right provider",
                    "too many similar offers",
                    "need clearer explanations before deciding",
                ],
                "desired_outcomes": [
                    "reduce decision friction",
                    "understand options more clearly",
                ],
                "suggested_page_types": ["faq", "services", "blog"],
            },
        ]
    else:
        groups = [
            {
                "group_name": "trust_clarity",
                "audience_intent": f"Users trying to understand the {niche_phrase} offer in {city_phrase}.",
                "pains": [
                    "lack of trust in unknown company",
                    "uncertainty about service quality",
                ],
                "desired_outcomes": [
                    "choose a reliable provider",
                    "understand the offer clearly",
                ],
                "suggested_page_types": ["home", "about"],
            },
            {
                "group_name": "pricing_scope",
                "audience_intent": f"Users comparing scope and price for {niche_phrase}.",
                "pains": [
                    "fear of overpaying",
                    "pricing is unclear",
                ],
                "desired_outcomes": [
                    "understand pricing",
                    "reduce decision friction",
                ],
                "suggested_page_types": ["services", "faq"],
            },
            {
                "group_name": "decision_support",
                "audience_intent": f"Users needing support before choosing a {niche_phrase} provider.",
                "pains": [
                    "difficulty choosing the right provider",
                    "need clearer explanations before deciding",
                ],
                "desired_outcomes": [
                    "choose a reliable provider",
                    "understand options more clearly",
                ],
                "suggested_page_types": ["services", "faq", "blog"],
            },
        ]

    normalized_groups = []
    for group in groups:
        suggested_page_types = normalize_page_type_list(group["suggested_page_types"], available_page_types)
        if "home" in tier_1_page_types and "home" in available_page_types and "home" not in suggested_page_types:
            suggested_page_types.append("home")

        normalized_groups.append(
            {
                "group_name": group["group_name"],
                "audience_intent": group["audience_intent"],
                "pains": group["pains"],
                "desired_outcomes": group["desired_outcomes"],
                "suggested_page_types": suggested_page_types,
            }
        )

    return normalized_groups


def collect_competitors(context: PipelineContext) -> PipelineContext:
    """Collect competitor data for the selected niche and city."""
    logger.info("collect_competitors received context for %s", context.input_data.get("project_name"))
    context.competitors = [
        f"stub competitors for {context.input_data.get('niche')} in {context.input_data.get('city')}"
    ]
    context = _save_step_artifact(context, "competitors", "competitors.json", context.competitors)
    return context


def extract_pains(context: PipelineContext) -> PipelineContext:
    """Extract customer pains and intent signals."""
    logger.info("extract_pains received context for %s", context.input_data.get("project_name"))
    input_data = context.input_data
    pages = context.site_structure.get("pages", [])
    available_page_types = {page.get("page_type", "") for page in pages}
    tier_1_page_types = {
        page.get("page_type", "")
        for page in context.seo_priorities.get("priority_pages", [])
        if page.get("priority_tier") == "tier_1"
    }

    pain_groups = build_pain_groups_for_site_type(
        site_type=input_data.get("site_type", ""),
        niche=input_data.get("niche", ""),
        city=input_data.get("city", ""),
        available_page_types=available_page_types,
        tier_1_page_types=tier_1_page_types,
    )

    context.pains = {
        "project_name": input_data.get("project_name"),
        "city": input_data.get("city"),
        "niche": input_data.get("niche"),
        "pain_groups": pain_groups,
        "summary": {
            "total_groups": len(pain_groups),
            "total_pains": count_total_pains(pain_groups),
        },
    }
    context = _save_step_artifact(context, "pains", "pains.json", context.pains)
    return context


def collect_semantics(context: PipelineContext) -> PipelineContext:
    """Collect keyword semantics for future SEO analysis."""
    logger.info("collect_semantics received context for %s", context.input_data.get("project_name"))
    input_data = context.input_data
    keyword_clusters = []

    for page in context.site_structure.get("pages", []):
        cluster = build_keywords_for_page(
            page=page,
            niche=input_data.get("niche", ""),
            city=input_data.get("city", ""),
        )
        if cluster is not None:
            keyword_clusters.append(cluster)

    context.semantics = {
        "project_name": input_data.get("project_name"),
        "niche": input_data.get("niche"),
        "city": input_data.get("city"),
        "language": input_data.get("language"),
        "keyword_clusters": keyword_clusters,
        "summary": {
            "total_clusters": len(keyword_clusters),
            "total_keywords": count_total_keywords(keyword_clusters),
        },
    }
    context = _save_step_artifact(context, "semantics", "semantics.json", context.semantics)
    return context


def build_gap_analysis(context: PipelineContext) -> PipelineContext:
    """Build a content and positioning gap analysis."""
    logger.info("build_gap_analysis received context for %s", context.input_data.get("project_name"))
    input_data = context.input_data
    keyword_clusters = context.semantics.get("keyword_clusters", [])
    priority_pages = {
        page["page_slug"]: page for page in context.seo_priorities.get("priority_pages", [])
    }
    build_spec_pages = {
        page["slug"]: page for page in context.build_spec.get("pages", [])
    }

    coverage_by_page = []
    for page in context.site_structure.get("pages", []):
        page_slug = page.get("slug", "")
        page_type = page.get("page_type", "")
        priority_page = priority_pages.get(page_slug, {})
        build_spec_page = build_spec_pages.get(page_slug, {})
        priority_tier = priority_page.get("priority_tier", get_priority_tier(page_type))
        cluster_count = get_cluster_count(page_slug, keyword_clusters)
        coverage_status = get_coverage_status(priority_tier, cluster_count)
        notes = get_coverage_notes(coverage_status)

        if build_spec_page.get("required_sections"):
            notes.append(
                f"Build spec defines {len(build_spec_page.get('required_sections', []))} required sections."
            )

        coverage_by_page.append(
            {
                "page_slug": page_slug,
                "page_type": page_type,
                "priority_tier": priority_tier,
                "cluster_count": cluster_count,
                "coverage_status": coverage_status,
                "notes": notes,
            }
        )

    covered_count = sum(1 for page in coverage_by_page if page["coverage_status"] == "covered")
    weak_count = sum(1 for page in coverage_by_page if page["coverage_status"] == "weak")
    missing_count = sum(1 for page in coverage_by_page if page["coverage_status"] == "missing")

    context.gap_analysis = {
        "project_name": input_data.get("project_name"),
        "city": input_data.get("city"),
        "niche": input_data.get("niche"),
        "coverage_by_page": coverage_by_page,
        "summary": {
            "covered_count": covered_count,
            "weak_count": weak_count,
            "missing_count": missing_count,
        },
        "recommendations": build_gap_recommendations(
            covered_count=covered_count,
            weak_count=weak_count,
            missing_count=missing_count,
        ),
    }
    context = _save_step_artifact(
        context,
        "gap_analysis",
        "gap_analysis.json",
        context.gap_analysis,
    )
    return context


def build_page_blueprints(context: PipelineContext) -> PipelineContext:
    """Build unified page-level blueprints from all existing artifacts."""
    logger.info("build_page_blueprints received context for %s", context.input_data.get("project_name"))
    input_data = context.input_data
    keyword_clusters = context.semantics.get("keyword_clusters", [])
    pain_groups = context.pains.get("pain_groups", [])
    priority_pages = {
        page["page_slug"]: page for page in context.seo_priorities.get("priority_pages", [])
    }
    build_spec_pages = {
        page["slug"]: page for page in context.build_spec.get("pages", [])
    }
    coverage_by_page = {
        page["page_slug"]: page for page in context.gap_analysis.get("coverage_by_page", [])
    }

    blueprint_pages = []
    for page in context.site_structure.get("pages", []):
        slug = page.get("slug", "")
        page_type = page.get("page_type", "")
        priority_page = priority_pages.get(slug, {})
        build_spec_page = build_spec_pages.get(slug, {})
        coverage_page = coverage_by_page.get(slug, {})
        target_cluster_names = priority_page.get("target_cluster_names", [])

        blueprint_pages.append(
            {
                "slug": slug,
                "page_type": page_type,
                "title_hint": page.get("title_hint", ""),
                "priority_tier": priority_page.get("priority_tier", ""),
                "primary_goal": priority_page.get("primary_goal", ""),
                "required_sections": build_spec_page.get("required_sections", []),
                "target_keywords": collect_keywords_for_clusters(target_cluster_names, keyword_clusters),
                "target_cluster_names": target_cluster_names,
                "relevant_pain_groups": get_relevant_pain_groups(page_type, pain_groups),
                "seo_notes": build_spec_page.get("seo_notes", []),
                "coverage_status": coverage_page.get("coverage_status", ""),
                "build_priority": get_build_priority(
                    priority_page.get("priority_tier", ""),
                    coverage_page.get("coverage_status", ""),
                ),
            }
        )

    context.page_blueprints = {
        "project_name": input_data.get("project_name"),
        "city": input_data.get("city"),
        "niche": input_data.get("niche"),
        "pages": blueprint_pages,
        "summary": {
            "total_pages": len(blueprint_pages),
            "tier_1_pages": sum(1 for page in blueprint_pages if page["priority_tier"] == "tier_1"),
            "tier_2_pages": sum(1 for page in blueprint_pages if page["priority_tier"] == "tier_2"),
            "tier_3_pages": sum(1 for page in blueprint_pages if page["priority_tier"] == "tier_3"),
        },
    }
    context = _save_step_artifact(
        context,
        "page_blueprints",
        "page_blueprints.json",
        context.page_blueprints,
    )
    return context


def build_execution_plan(context: PipelineContext) -> PipelineContext:
    """Build a deterministic site execution plan from page blueprints."""
    logger.info("build_execution_plan received context for %s", context.input_data.get("project_name"))
    input_data = context.input_data
    blueprint_pages = context.page_blueprints.get("pages", [])
    sorted_pages = sorted(blueprint_pages, key=get_execution_sort_key)

    build_sequence = []
    for index, page in enumerate(sorted_pages, start=1):
        required_sections = page.get("required_sections", [])
        build_sequence.append(
            {
                "step_number": index,
                "page_slug": page.get("slug", ""),
                "page_type": page.get("page_type", ""),
                "build_priority": page.get("build_priority", ""),
                "why_now": get_why_now(page),
                "depends_on": get_depends_on(page),
                "ready": bool(required_sections),
            }
        )

    phase_summary = get_phase_summary(sorted_pages)
    context.execution_plan = {
        "project_name": input_data.get("project_name"),
        "city": input_data.get("city"),
        "niche": input_data.get("niche"),
        "build_sequence": build_sequence,
        "phase_summary": phase_summary,
        "summary": {
            "total_pages": len(build_sequence),
            "high_priority_count": sum(
                1 for page in build_sequence if page["build_priority"] in {"high", "urgent"}
            ),
            "medium_priority_count": sum(
                1 for page in build_sequence if page["build_priority"] == "medium"
            ),
            "low_priority_count": sum(
                1 for page in build_sequence if page["build_priority"] == "low"
            ),
        },
    }
    context = _save_step_artifact(
        context,
        "execution_plan",
        "execution_plan.json",
        context.execution_plan,
    )
    return context


def build_project_package(context: PipelineContext) -> PipelineContext:
    """Build a single aggregated project package from all pipeline artifacts."""
    logger.info("build_project_package received context for %s", context.input_data.get("project_name"))

    page_summary = context.page_blueprints.get("summary", {})

    context.project_package = {
        "project_name": context.input_data.get("project_name", ""),
        "input_data": context.input_data or {},
        "artifacts_index": context.artifacts_index or {},
        "site_structure": context.site_structure or {},
        "build_spec": context.build_spec or {},
        "semantics": context.semantics or {},
        "seo_priorities": context.seo_priorities or {},
        "pains": context.pains or {},
        "gap_analysis": context.gap_analysis or {},
        "page_blueprints": context.page_blueprints or {},
        "execution_plan": context.execution_plan or {},
        "summary": {
            "total_artifacts": len(context.artifacts_index),
            "total_pages": page_summary.get("total_pages", 0),
            "tier_1_pages": page_summary.get("tier_1_pages", 0),
            "tier_2_pages": page_summary.get("tier_2_pages", 0),
            "tier_3_pages": page_summary.get("tier_3_pages", 0),
        },
    }
    context = _save_step_artifact(
        context,
        "project_package",
        "project_package.json",
        context.project_package,
    )
    return context


def make_task_id(page_slug: str, task_type: str, section_name: str = "") -> str:
    base = f"{page_slug}__{task_type}"
    if section_name:
        base = f"{base}__{section_name}"
    return slugify(base.replace("_", "-"))


def get_content_requirements(section_name: str) -> list[str]:
    requirements_map = {
        "hero": ["clear value proposition", "local relevance mention", "strong CTA"],
        "services_overview": ["list of key services", "scannable structure", "internal linking potential"],
        "services_list": ["list of key services", "scannable structure", "internal linking potential"],
        "trust_signals": ["credibility elements", "reassurance"],
        "faq_preview": ["objections and common questions", "concise answers"],
        "faq_list": ["objections and common questions", "concise answers"],
        "contact_cta": ["friction reduction", "strong conversion intent"],
        "contact_form": ["friction reduction", "strong conversion intent"],
        "contact_details": ["friction reduction", "strong conversion intent"],
        "service_description": ["service scope", "benefits", "local applicability"],
        "benefits": ["outcome-focused points", "trust/supporting value"],
        "local_relevance": ["geographic clarity", "local coverage relevance"],
        "service_area_summary": ["geographic clarity", "local coverage relevance"],
        "areas_list": ["geographic clarity", "local coverage relevance"],
        "company_story": ["trust building", "brand credibility"],
        "team_or_values": ["trust building", "brand credibility"],
        "process": ["simple step-by-step explanation"],
        "blog_index": ["informational support content organization"],
        "service_summary": ["geographic clarity", "local coverage relevance"],
    }
    return requirements_map.get(section_name, [])


def get_section_focus(section_name: str) -> str:
    focus_map = {
        "hero": "positioning and conversion",
        "services_overview": "service clarity",
        "services_list": "service clarity",
        "trust_signals": "trust and reassurance",
        "faq_preview": "objections handling",
        "faq_list": "objections handling",
        "contact_cta": "conversion and action",
        "contact_form": "conversion and action",
        "contact_details": "conversion and action",
        "service_description": "scope and relevance",
        "benefits": "outcomes and value",
        "local_relevance": "local coverage",
        "service_area_summary": "local coverage",
        "areas_list": "local coverage",
        "company_story": "trust and brand credibility",
        "team_or_values": "trust and brand credibility",
        "process": "clarity of engagement",
        "blog_index": "informational content structure",
    }
    return focus_map.get(section_name, "structured support content")


def get_cta_intent(section_name: str) -> str:
    if section_name in {"hero", "contact_cta", "contact_form", "contact_details"}:
        return "contact_now"
    if section_name in {"service_description", "services_list", "services_overview"}:
        return "explore_services"
    if section_name in {"faq_preview", "faq_list", "blog_index"}:
        return "reduce_friction"
    if section_name in {"trust_signals", "company_story", "team_or_values"}:
        return "build_trust"
    if section_name in {"local_relevance", "service_area_summary", "areas_list", "service_summary"}:
        return "confirm_local_fit"
    return "learn_more"


def collect_pain_payload(
    relevant_pain_groups: list[str],
    pain_groups: list[dict[str, object]],
) -> tuple[list[str], list[str]]:
    pain_points = []
    desired_outcomes = []

    for group in pain_groups:
        if group.get("group_name") in relevant_pain_groups:
            pain_points.extend(group.get("pains", []))
            desired_outcomes.extend(group.get("desired_outcomes", []))

    return dedupe_keywords(pain_points), dedupe_keywords(desired_outcomes)


def unique_preserve_order(values: list[str]) -> list[str]:
    unique_values = []
    seen = set()

    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)

    return unique_values


def get_phase_note(phase_name: str) -> str:
    notes = {
        "phase_1_foundation_high": "Start with highest-priority revenue-driving sections.",
        "phase_2_medium_support": "Continue with support and expansion sections.",
        "phase_3_low_later": "Finish lower-priority trust and content sections.",
    }
    return notes.get(phase_name, "Process grouped batches in planned order.")


def build_page_task_queue(context: PipelineContext) -> PipelineContext:
    """Build deterministic page task queue from page blueprints and execution plan."""
    logger.info("build_page_task_queue received context for %s", context.input_data.get("project_name"))

    blueprint_pages = {
        page["slug"]: page for page in context.page_blueprints.get("pages", [])
    }
    execution_steps = {
        step["page_slug"]: step for step in context.execution_plan.get("build_sequence", [])
    }

    tasks = []
    page_level_tasks = 0
    section_level_tasks = 0

    for page_slug, step in execution_steps.items():
        page = blueprint_pages.get(page_slug, {})
        page_type = page.get("page_type", "")
        required_sections = page.get("required_sections", [])
        priority = page.get("build_priority", "low")
        ready = bool(required_sections)

        page_setup_task_id = make_task_id(page_slug, "page-setup")
        tasks.append(
            {
                "task_id": page_setup_task_id,
                "page_slug": page_slug,
                "page_type": page_type,
                "task_type": "page_setup",
                "section_name": "",
                "priority": priority,
                "depends_on": step.get("depends_on", []),
                "input_sources": ["page_blueprints", "execution_plan"],
                "description": f"Prepare base page shell for {page_slug}.",
                "ready": ready,
            }
        )
        page_level_tasks += 1

        section_task_ids = []
        for section_name in required_sections:
            section_task_id = make_task_id(page_slug, "section-build", section_name)
            section_task_ids.append(section_task_id)
            tasks.append(
                {
                    "task_id": section_task_id,
                    "page_slug": page_slug,
                    "page_type": page_type,
                    "task_type": "section_build",
                    "section_name": section_name,
                    "priority": priority,
                    "depends_on": [page_setup_task_id],
                    "input_sources": ["page_blueprints", "build_spec", "pains", "semantics"],
                    "description": f"Build {section_name} section for {page_slug}.",
                    "ready": ready,
                }
            )
            section_level_tasks += 1

        tasks.append(
            {
                "task_id": make_task_id(page_slug, "seo-finalize"),
                "page_slug": page_slug,
                "page_type": page_type,
                "task_type": "seo_finalize",
                "section_name": "",
                "priority": priority,
                "depends_on": section_task_ids,
                "input_sources": ["page_blueprints", "semantics", "seo_priorities"],
                "description": f"Finalize SEO metadata and on-page structure for {page_slug}.",
                "ready": ready,
            }
        )
        page_level_tasks += 1

    context.page_task_queue = {
        "project_name": context.input_data.get("project_name", ""),
        "city": context.input_data.get("city", ""),
        "niche": context.input_data.get("niche", ""),
        "tasks": tasks,
        "summary": {
            "total_tasks": len(tasks),
            "page_level_tasks": page_level_tasks,
            "section_level_tasks": section_level_tasks,
            "high_priority_tasks": sum(1 for task in tasks if task["priority"] in {"high", "urgent"}),
            "medium_priority_tasks": sum(1 for task in tasks if task["priority"] == "medium"),
            "low_priority_tasks": sum(1 for task in tasks if task["priority"] == "low"),
        },
    }
    context = _save_step_artifact(
        context,
        "page_task_queue",
        "page_task_queue.json",
        context.page_task_queue,
    )
    return context


def build_section_briefs(context: PipelineContext) -> PipelineContext:
    """Build structured section briefs from section-level page tasks."""
    logger.info("build_section_briefs received context for %s", context.input_data.get("project_name"))

    blueprint_pages = {
        page["slug"]: page for page in context.page_blueprints.get("pages", [])
    }

    briefs = []
    for task in context.page_task_queue.get("tasks", []):
        if task.get("task_type") != "section_build":
            continue

        page_slug = task.get("page_slug", "")
        section_name = task.get("section_name", "")
        page_blueprint = blueprint_pages.get(page_slug, {})
        content_requirements = get_content_requirements(section_name)

        briefs.append(
            {
                "brief_id": make_task_id(page_slug, "brief", section_name),
                "task_id": task.get("task_id", ""),
                "page_slug": page_slug,
                "page_type": task.get("page_type", ""),
                "section_name": section_name,
                "priority": task.get("priority", ""),
                "primary_goal": page_blueprint.get("primary_goal", ""),
                "target_keywords": page_blueprint.get("target_keywords", []),
                "relevant_pain_groups": page_blueprint.get("relevant_pain_groups", []),
                "seo_notes": page_blueprint.get("seo_notes", []),
                "content_requirements": content_requirements,
                "input_sources": task.get("input_sources", []),
                "ready": bool(page_slug and section_name and content_requirements),
            }
        )

    context.section_briefs = {
        "project_name": context.input_data.get("project_name", ""),
        "city": context.input_data.get("city", ""),
        "niche": context.input_data.get("niche", ""),
        "sections": briefs,
        "summary": {
            "total_section_briefs": len(briefs),
            "high_priority_briefs": sum(1 for brief in briefs if brief["priority"] in {"high", "urgent"}),
            "medium_priority_briefs": sum(1 for brief in briefs if brief["priority"] == "medium"),
            "low_priority_briefs": sum(1 for brief in briefs if brief["priority"] == "low"),
        },
    }
    context = _save_step_artifact(
        context,
        "section_briefs",
        "section_briefs.json",
        context.section_briefs,
    )
    return context


def build_generation_manifest(context: PipelineContext) -> PipelineContext:
    """Build a consumer-ready manifest from generation batches."""
    logger.info("build_generation_manifest received context for %s", context.input_data.get("project_name"))

    generation_batches = context.generation_batches or {}
    batch_list = generation_batches.get("batches", [])
    phase_order = generation_batches.get("phase_order", [])
    batch_by_id = {batch.get("batch_id", ""): batch for batch in batch_list}
    phase_by_batch_id = {
        batch_id: phase.get("phase_name", "")
        for phase in phase_order
        for batch_id in phase.get("batch_ids", [])
    }

    phases = []
    for phase in phase_order:
        phase_name = str(phase.get("phase_name", ""))
        batch_ids = phase.get("batch_ids", [])
        phase_batches = [batch_by_id[batch_id] for batch_id in batch_ids if batch_id in batch_by_id]

        phases.append(
            {
                "phase_name": phase_name,
                "batch_ids": batch_ids,
                "item_count": sum(int(batch.get("total_items", 0)) for batch in phase_batches),
                "priority_levels": unique_preserve_order(
                    [str(batch.get("priority", "")) for batch in phase_batches]
                ),
                "notes": get_phase_note(phase_name),
            }
        )

    manifest_batches = []
    for batch in batch_list:
        item_count = int(batch.get("total_items", 0))
        ready_count = int(batch.get("ready_count", 0))
        manifest_batches.append(
            {
                "batch_id": batch.get("batch_id", ""),
                "phase_name": phase_by_batch_id.get(batch.get("batch_id", ""), ""),
                "priority": batch.get("priority", ""),
                "page_type": batch.get("page_type", ""),
                "item_count": item_count,
                "ready_count": ready_count,
                "input_artifacts": ["project_package", "content_input_queue", "generation_batches"],
                "execution_mode": "section_stub_generation",
                "ready": ready_count == item_count,
            }
        )

    context.generation_manifest = {
        "project_name": context.input_data.get("project_name", ""),
        "city": context.input_data.get("city", ""),
        "niche": context.input_data.get("niche", ""),
        "consumer_name": "local_section_generator",
        "manifest_version": "v1",
        "phases": phases,
        "batches": manifest_batches,
        "execution_rules": {
            "process_phases_in_order": True,
            "skip_unready_batches": True,
            "batch_execution_mode": "sequential_by_phase",
            "item_execution_mode": "sequential_within_batch",
        },
        "input_artifacts": {
            "project_package": context.artifacts_index.get("project_package", ""),
            "content_input_queue": context.artifacts_index.get("content_input_queue", ""),
            "generation_batches": context.artifacts_index.get("generation_batches", ""),
        },
        "summary": {
            "total_phases": len(phases),
            "total_batches": len(manifest_batches),
            "total_items": sum(int(batch.get("item_count", 0)) for batch in manifest_batches),
            "ready_batches": sum(1 for batch in manifest_batches if batch.get("ready") is True),
        },
    }
    context = _save_step_artifact(
        context,
        "generation_manifest",
        "generation_manifest.json",
        context.generation_manifest,
    )
    return context


def build_generation_batches(context: PipelineContext) -> PipelineContext:
    """Group content input items into deterministic batches for future generation."""
    logger.info("build_generation_batches received context for %s", context.input_data.get("project_name"))

    grouped_items: dict[tuple[str, str], list[dict[str, object]]] = {}

    for item in context.content_input_queue.get("items", []):
        priority = str(item.get("priority", "low"))
        page_type = str(item.get("page_type", "unknown"))
        group_key = (priority, page_type)
        grouped_items.setdefault(group_key, []).append(item)

    batches = []
    for priority, page_type in sorted(grouped_items.keys(), key=lambda key: (key[0], key[1])):
        items = grouped_items[(priority, page_type)]
        batches.append(
            {
                "batch_id": f"{priority}__{page_type}",
                "batch_type": "priority_page_type_group",
                "priority": priority,
                "page_type": page_type,
                "item_ids": [str(item.get("item_id", "")) for item in items],
                "page_slugs": unique_preserve_order([str(item.get("page_slug", "")) for item in items]),
                "section_names": unique_preserve_order([str(item.get("section_name", "")) for item in items]),
                "ready_count": sum(1 for item in items if item.get("ready") is True),
                "total_items": len(items),
            }
        )

    high_batch_ids = [batch["batch_id"] for batch in batches if batch["priority"] in {"high", "urgent"}]
    medium_batch_ids = [batch["batch_id"] for batch in batches if batch["priority"] == "medium"]
    low_batch_ids = [batch["batch_id"] for batch in batches if batch["priority"] == "low"]

    context.generation_batches = {
        "project_name": context.input_data.get("project_name", ""),
        "city": context.input_data.get("city", ""),
        "niche": context.input_data.get("niche", ""),
        "batches": batches,
        "phase_order": [
            {
                "phase_name": "phase_1_foundation_high",
                "batch_ids": high_batch_ids,
            },
            {
                "phase_name": "phase_2_medium_support",
                "batch_ids": medium_batch_ids,
            },
            {
                "phase_name": "phase_3_low_later",
                "batch_ids": low_batch_ids,
            },
        ],
        "summary": {
            "total_batches": len(batches),
            "total_items_grouped": sum(batch["total_items"] for batch in batches),
            "high_priority_batches": len(high_batch_ids),
            "medium_priority_batches": len(medium_batch_ids),
            "low_priority_batches": len(low_batch_ids),
        },
    }
    context = _save_step_artifact(
        context,
        "generation_batches",
        "generation_batches.json",
        context.generation_batches,
    )
    return context


def build_content_input_queue(context: PipelineContext) -> PipelineContext:
    """Build structured content input payloads from section briefs."""
    logger.info("build_content_input_queue received context for %s", context.input_data.get("project_name"))

    pain_groups = context.pains.get("pain_groups", [])
    items = []

    for brief in context.section_briefs.get("sections", []):
        section_name = brief.get("section_name", "")
        relevant_pain_groups = brief.get("relevant_pain_groups", [])
        pain_points, desired_outcomes = collect_pain_payload(relevant_pain_groups, pain_groups)

        items.append(
            {
                "item_id": f"{brief.get('page_slug', '')}--content-input--{section_name}",
                "brief_id": brief.get("brief_id", ""),
                "page_slug": brief.get("page_slug", ""),
                "page_type": brief.get("page_type", ""),
                "section_name": section_name,
                "priority": brief.get("priority", ""),
                "generation_mode": "section_content_stub",
                "content_payload": {
                    "primary_goal": brief.get("primary_goal", ""),
                    "target_keywords": brief.get("target_keywords", []),
                    "pain_points": pain_points,
                    "desired_outcomes": desired_outcomes,
                    "seo_notes": brief.get("seo_notes", []),
                    "content_requirements": brief.get("content_requirements", []),
                    "section_focus": get_section_focus(section_name),
                    "cta_intent": get_cta_intent(section_name),
                },
                "input_sources": brief.get("input_sources", []),
                "ready": bool(
                    brief.get("page_slug")
                    and section_name
                    and brief.get("content_requirements")
                ),
            }
        )

    context.content_input_queue = {
        "project_name": context.input_data.get("project_name", ""),
        "city": context.input_data.get("city", ""),
        "niche": context.input_data.get("niche", ""),
        "items": items,
        "summary": {
            "total_items": len(items),
            "high_priority_items": sum(1 for item in items if item["priority"] in {"high", "urgent"}),
            "medium_priority_items": sum(1 for item in items if item["priority"] == "medium"),
            "low_priority_items": sum(1 for item in items if item["priority"] == "low"),
        },
    }
    context = _save_step_artifact(
        context,
        "content_input_queue",
        "content_input_queue.json",
        context.content_input_queue,
    )
    return context


def build_seo_priorities(context: PipelineContext) -> PipelineContext:
    """Define SEO priorities for the generated site."""
    logger.info("build_seo_priorities received context for %s", context.input_data.get("project_name"))
    input_data = context.input_data
    keyword_clusters = context.semantics.get("keyword_clusters", [])
    priority_pages = []

    for page in context.build_spec.get("pages", []):
        page_slug = page.get("slug", "")
        page_type = page.get("page_type", "")
        priority_tier = get_priority_tier(page_type)

        priority_pages.append(
            {
                "page_slug": page_slug,
                "page_type": page_type,
                "priority_tier": priority_tier,
                "primary_goal": get_primary_goal(page_type),
                "target_cluster_names": get_target_cluster_names(page_slug, keyword_clusters),
                "reason": get_priority_reason(page_type, priority_tier),
            }
        )

    context.seo_priorities = {
        "project_name": input_data.get("project_name"),
        "city": input_data.get("city"),
        "niche": input_data.get("niche"),
        "priority_pages": priority_pages,
        "summary": {
            "tier_1_count": sum(1 for page in priority_pages if page["priority_tier"] == "tier_1"),
            "tier_2_count": sum(1 for page in priority_pages if page["priority_tier"] == "tier_2"),
            "tier_3_count": sum(1 for page in priority_pages if page["priority_tier"] == "tier_3"),
        },
    }
    context = _save_step_artifact(
        context,
        "seo_priorities",
        "seo_priorities.json",
        context.seo_priorities,
    )
    return context


def build_site_structure(context: PipelineContext) -> PipelineContext:
    """Build a draft site structure."""
    logger.info("build_site_structure received context for %s", context.input_data.get("project_name"))
    input_data = context.input_data
    niche = input_data.get("niche", "")
    city = input_data.get("city", "")
    site_type = input_data.get("site_type", "")
    max_pages = int(input_data.get("max_pages", 0))
    include_blog = bool(input_data.get("include_blog", False))

    pages = build_base_pages(niche, city, site_type, include_blog)

    if max_pages >= 10:
        pages.extend(build_service_pages(niche, city))

    if max_pages >= 15:
        pages.extend(build_location_pages(niche, city))

    pages = pages[:max_pages]

    context.site_structure = {
        "site_name": input_data.get("project_name"),
        "site_type": site_type,
        "city": city,
        "pages": pages,
    }
    context = _save_step_artifact(
        context,
        "site_structure",
        "site_structure.json",
        context.site_structure,
    )
    return context


def build_build_spec(context: PipelineContext) -> PipelineContext:
    """Build a specification for site generation."""
    logger.info("build_build_spec received context for %s", context.input_data.get("project_name"))
    input_data = context.input_data
    site_structure = context.site_structure
    templates = get_template_sections()

    pages = []
    for page in site_structure.get("pages", []):
        page_type = page.get("page_type", "")
        pages.append(
            {
                "slug": page.get("slug", ""),
                "page_type": page_type,
                "title_hint": page.get("title_hint", ""),
                "required_sections": templates.get(page_type, []),
                "seo_notes": get_page_type_seo_notes(page_type),
            }
        )

    context.build_spec = {
        "project_name": input_data.get("project_name"),
        "site_type": input_data.get("site_type"),
        "language": input_data.get("language"),
        "city": input_data.get("city"),
        "niche": input_data.get("niche"),
        "global_rules": {
            "include_images": input_data.get("include_images", False),
            "include_blog": input_data.get("include_blog", False),
            "max_pages": input_data.get("max_pages", 0),
            "budget_mode": input_data.get("budget_mode", ""),
        },
        "templates": templates,
        "pages": pages,
    }
    context = _save_step_artifact(
        context,
        "build_spec",
        "build_spec.json",
        context.build_spec,
    )
    return context
