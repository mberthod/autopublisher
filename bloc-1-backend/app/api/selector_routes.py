import copy

from fastapi import APIRouter, HTTPException

router = APIRouter()

SELECTORS: dict[str, dict] = {
    "2026-07-01-v1": {
        "version": "2026-07-01-v1",
        "updated_at": "2026-07-01T10:00:00Z",
        "min_extension_version": "0.1.0",
        "platforms": {
            "linkedin": {
                "btn_open_compose": "button[aria-label='Commencer un post']",
                "text_editor": "div[role='textbox']",
                "file_input": "input[type='file'][accept*='image']",
                "btn_submit": "button.share-actions__primary-action",
                "btn_post_publish": "button[aria-label='Publier']",
                "success_toast": "div[role='alert']",
            },
            "instagram": {
                "btn_new_post": "svg[aria-label='Nouvelle publication']",
                "btn_select_file": "button",
                "file_input": "input[type='file']",
                "next_button": "button",
                "caption_editor": "textarea[aria-label='Écrire une légende']",
                "share_button": "button",
            },
        },
    },
    "2026-07-04-v2": {
        "version": "2026-07-04-v2",
        "updated_at": "2026-07-04T08:00:00Z",
        "min_extension_version": "0.1.0",
        "platforms": {
            "linkedin": {
                "btn_open_compose": "button[aria-label='Commencer un post'], button[aria-label='Start a post']",
                "text_editor": "div[role='textbox'][contenteditable='true']",
                "file_input": "input[type='file'][accept*='image']",
                "btn_submit": "button.share-actions__primary-action",
                "btn_post_publish": "button[aria-label='Publier'], button[aria-label='Post']",
                "success_toast": "div[role='alert']",
            },
            "instagram": {
                "btn_new_post": "svg[aria-label='Nouvelle publication'], svg[aria-label='New post']",
                "file_input": "input[type='file']",
                "next_button": "div[role='button']",
                "caption_editor": "textarea[aria-label='Écrire une légende…'], textarea[aria-label='Write a caption...'], textarea[aria-label='Écrire une légende']",
                "share_button": "div[role='button']",
                "success_indicator": "div[role='alert'], article header",
            },
        },
    },
    "2026-07-04-v3": {
        "version": "2026-07-04-v3",
        "updated_at": "2026-07-04T12:00:00Z",
        "min_extension_version": "0.1.0",
        "platforms": {
            "linkedin": {
                # btn_open_compose est un fallback — le publisher essaie d'abord
                # de detecter le compositeur deja ouvert via ?shareActive=true
                "btn_open_compose": (
                    "button[aria-label='Commencer un post'], "
                    "button[aria-label='Start a post'], "
                    ".share-box-feed-entry__trigger, "
                    "div.share-box-feed-entry__top-bar button, "
                    "button[class*='share'][class*='trigger']"
                ),
                "text_editor": (
                    "div[role='textbox'][contenteditable='true'], "
                    "div.ql-editor[contenteditable='true'], "
                    "div[contenteditable='true'][data-placeholder]"
                ),
                "file_input": "input[type='file'][accept*='image'], input[type='file']",
                "btn_submit": (
                    "button.share-actions__primary-action, "
                    "button[class*='share-actions__primary'], "
                    "button[aria-label='Publier'], "
                    "button[aria-label='Post']"
                ),
                "success_toast": "div[role='alert'], div[class*='artdeco-toast']",
            },
            "instagram": {
                "btn_new_post": (
                    "svg[aria-label='Nouvelle publication'], "
                    "svg[aria-label='New post'], "
                    "a[aria-label='Nouvelle publication'], "
                    "a[aria-label='New post']"
                ),
                "file_input": "input[type='file']",
                "next_button": "div[role='button']",
                "caption_editor": (
                    "textarea[aria-label='Écrire une légende…'], "
                    "textarea[aria-label='Write a caption...'], "
                    "textarea[aria-label='Écrire une légende']"
                ),
                "share_button": "div[role='button']",
                "success_indicator": "div[role='alert'], article header",
            },
        },
    },
    "2026-07-04-v4": {
        "version": "2026-07-04-v4",
        "updated_at": "2026-07-04T18:00:00Z",
        "min_extension_version": "0.1.0",
        "platforms": {
            "linkedin": {
                # Source de verite unique : le publisher ne contient plus de
                # selecteurs en dur, tout vient d'ici (cascades FR + EN).
                "btn_open_compose": (
                    "button[aria-label='Commencer un post'], "
                    "button[aria-label='Start a post'], "
                    "button[aria-label='Créer un post'], "
                    "button[aria-label='Create a post'], "
                    ".share-box-feed-entry__trigger, "
                    "div.share-box-feed-entry__top-bar button, "
                    "div[class*='share-box'] button, "
                    "button[class*='share'][class*='trigger'], "
                    "button[class*='create-post'], "
                    "button[class*='compose']"
                ),
                "text_editor": (
                    "div[role='textbox'][contenteditable='true'], "
                    "div.ql-editor[contenteditable='true'], "
                    "div[contenteditable='true'][data-placeholder], "
                    "div[contenteditable='true'].editor-content, "
                    "div[contenteditable='true'], "
                    "[contenteditable='true']"
                ),
                "file_input": "input[type='file'][accept*='image'], input[type='file']",
                "btn_submit": (
                    "button.share-actions__primary-action, "
                    "button[class*='share-actions__primary'], "
                    "button[aria-label='Publier'], "
                    "button[aria-label='Post'], "
                    "button[aria-label='Partager'], "
                    "button[aria-label='Share']"
                ),
                "identity_picker_trigger": (
                    "button[aria-label*='Choisissez'], "
                    "button[aria-label*='Choose'], "
                    "button[aria-label*='identite'], "
                    "button[aria-label*='identity'], "
                    "div[class*='actor'] button, "
                    "div[class*='identity'] button, "
                    ".share-creation-state__actor-trigger, "
                    "button[class*='actor']"
                ),
                "identity_option": (
                    "[role='option'], "
                    "[role='radio'], "
                    "li[class*='actor'], "
                    "div[class*='actor-option'], "
                    "div[class*='identity-option']"
                ),
                "actor_name": (
                    ".share-creation-state__actor-name, "
                    "button[class*='actor'] span[class*='name'], "
                    ".share-creation-state__actor-trigger, "
                    "div[class*='share-actor'] span, "
                    "div[class*='actor'] button"
                ),
                "success_toast": "div[role='alert'], div[class*='artdeco-toast']",
                "success_toast_link": (
                    "div[role='alert'] a[href*='/feed/update/'], "
                    "div[class*='artdeco-toast'] a[href*='/feed/update/'], "
                    "div[class*='artdeco-toast'] a[href*='urn:li:activity']"
                ),
            },
            "instagram": {
                "btn_new_post": (
                    "svg[aria-label='Nouvelle publication'], "
                    "svg[aria-label='New post'], "
                    "a[aria-label='Nouvelle publication'], "
                    "a[aria-label='New post']"
                ),
                "file_input": "input[type='file']",
                "next_button": "div[role='button']",
                "caption_editor": (
                    "textarea[aria-label='Écrire une légende…'], "
                    "textarea[aria-label='Write a caption...'], "
                    "textarea[aria-label='Écrire une légende']"
                ),
                "share_button": "div[role='button']",
                "success_indicator": "div[role='alert'], article header",
            },
        },
    },
}

# v5 = v4 + section meta_suite (Meta Business Suite : pages Facebook + comptes
# Instagram pro). DOM Meta obfusque : selecteurs bases sur aria-label/role
# FR+EN, a affiner lors de la recette manuelle.
SELECTORS["2026-07-04-v5"] = {
    "version": "2026-07-04-v5",
    "updated_at": "2026-07-04T20:00:00Z",
    "min_extension_version": "0.1.0",
    "platforms": {
        **SELECTORS["2026-07-04-v4"]["platforms"],
        "meta_suite": {
            "account_switcher_trigger": (
                "div[role='button'][aria-label*='compte'], "
                "div[role='button'][aria-label*='account'], "
                "div[aria-label='Changer de compte'], "
                "div[aria-label='Switch account']"
            ),
            "account_option": (
                "div[role='dialog'] div[role='button'], "
                "div[role='listbox'] div[role='option'], "
                "[role='menuitem']"
            ),
            "active_account_name": (
                "div[role='banner'] div[role='button'] span, "
                "div[aria-label*='Changer de compte'] span, "
                "div[aria-label*='Switch account'] span"
            ),
            "btn_create_post": (
                "div[role='button'][aria-label*='Créer une publication'], "
                "div[role='button'][aria-label*='Create post'], "
                "a[href*='/composer'], "
                "div[role='button'][aria-label*='Créer'], "
                "div[role='button'][aria-label*='Create']"
            ),
            "placement_option_facebook": (
                "div[role='checkbox'][aria-label*='Facebook'], "
                "input[type='checkbox'][aria-label*='Facebook']"
            ),
            "placement_option_instagram": (
                "div[role='checkbox'][aria-label*='Instagram'], "
                "input[type='checkbox'][aria-label*='Instagram']"
            ),
            "text_editor": (
                "div[role='textbox'][contenteditable='true'], "
                "div[contenteditable='true'][data-lexical-editor], "
                "div[contenteditable='true']"
            ),
            "file_input": "input[type='file'][accept*='image'], input[type='file']",
            "btn_add_media": (
                "div[role='button'][aria-label*='photo'], "
                "div[role='button'][aria-label*='Photo'], "
                "div[role='button'][aria-label*='média'], "
                "div[role='button'][aria-label*='media']"
            ),
            "btn_publish": (
                "div[role='button'][aria-label='Publier'], "
                "div[role='button'][aria-label='Publish'], "
                "div[aria-label='Publier'][tabindex='0'], "
                "div[aria-label='Publish'][tabindex='0']"
            ),
            "success_indicator": (
                "div[role='alert'], "
                "div[aria-label*='publiée'], "
                "div[aria-label*='published']"
            ),
        },
    },
}

# v6 : Instagram a remplace le <textarea> de legende par un <div contenteditable>.
# On elargit caption_editor (et next/share restent gerees par texte cote publisher).
SELECTORS["2026-07-04-v6"] = copy.deepcopy(SELECTORS["2026-07-04-v5"])
SELECTORS["2026-07-04-v6"]["version"] = "2026-07-04-v6"
SELECTORS["2026-07-04-v6"]["platforms"]["instagram"]["caption_editor"] = (
    "div[aria-label='Écrire une légende…'][contenteditable='true'], "
    "div[aria-label='Write a caption...'][contenteditable='true'], "
    "div[aria-label*='légende'][contenteditable='true'], "
    "div[aria-label*='caption'][contenteditable='true'], "
    "div[role='textbox'][contenteditable='true'], "
    "div[contenteditable='true'][data-lexical-editor='true'], "
    "textarea[aria-label='Écrire une légende…'], "
    "textarea[aria-label='Write a caption...']"
)

LATEST_VERSION = "2026-07-04-v6"


@router.get("/latest")
def get_latest_selectors():
    return SELECTORS[LATEST_VERSION]


@router.get("/{version}")
def get_selectors(version: str):
    if version not in SELECTORS:
        raise HTTPException(status_code=404, detail=f"Selectors version {version} not found")
    return SELECTORS[version]
