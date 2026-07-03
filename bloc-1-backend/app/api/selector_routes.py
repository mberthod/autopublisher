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
    }
}

LATEST_VERSION = "2026-07-01-v1"


@router.get("/latest")
def get_latest_selectors():
    return SELECTORS[LATEST_VERSION]


@router.get("/{version}")
def get_selectors(version: str):
    if version not in SELECTORS:
        raise HTTPException(status_code=404, detail=f"Selectors version {version} not found")
    return SELECTORS[version]
