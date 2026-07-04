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
}

LATEST_VERSION = "2026-07-04-v3"


@router.get("/latest")
def get_latest_selectors():
    return SELECTORS[LATEST_VERSION]


@router.get("/{version}")
def get_selectors(version: str):
    if version not in SELECTORS:
        raise HTTPException(status_code=404, detail=f"Selectors version {version} not found")
    return SELECTORS[version]
