from app.config import Settings


def test_optional_dedicated_browser_profile_setting() -> None:
    settings = Settings(kbl_browser_user_data_dir="C:/kbl-predictor-browser-profile")
    assert settings.kbl_browser_user_data_dir == "C:/kbl-predictor-browser-profile"
