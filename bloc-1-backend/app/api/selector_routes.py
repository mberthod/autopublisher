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
                # French + English aria-labels for international accounts
                "btn_open_compose": "button[aria-label='Commencer un post'], button[aria-label='Start a post']",
                "text_editor": "div[role='textbox'][contenteditable='true']",
                "file_input": "input[type='file'][accept*='image']",
                "btn_submit": "button.share-actions__primary-action",
                "btn_post_publish": "button[aria-label='Publier'], button[aria-label='Post']",
                "success_toast": "div[role='alert']",
            },
            "instagram": {
                # More specific selectors — aria-label in FR and EN
                "btn_new_post": "svg[aria-label='Nouvelle publication'], svg[aria-label='New post']",
                "file_input": "input[type='file']",
                # Instagram's "Suivant/Next" is a styled div button, not a <button>
                "next_button": "div[role='button']",
                # Caption textarea — FR and EN
                "caption_editor": "textarea[aria-label='Écrire une légende…'], textarea[aria-label='Write a caption...'], textarea[aria-label='Écrire une légende']",
                # Share button — look for the div role=button with specific text via xpath in publisher
                "share_button": "div[role='button']",
                # Success: the dialog closes and a post appears, or a specific toast
                "success_indicator": "div[role='alert'], article header",
            },
        },
    },
}

LATEST_VERSION = "2026-07-04-v2"


@router.get("/latest")
def get_latest_selectors():
    return SELECTORS[LATEST_VERSION]


@router.get("/{version}")
def get_selectors(version: str):
    if version not in SELECTORS:
        raise HTTPException(status_code=404, detail=f"Selectors version {version} not found")
    return SELECTORS[version]
