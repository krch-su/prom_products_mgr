from __future__ import annotations

import asyncio
# import asyncio
from typing import TYPE_CHECKING, Any, ClassVar, List
from urllib.parse import quote

from install_playwright import install
from playwright._impl._errors import Error as PlaywrightError
# from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright

if TYPE_CHECKING:
    from collections.abc import Coroutine

    from playwright.sync_api._generated import Browser, Playwright


class DeepLCLIError(Exception):
    pass


class DeepLCLIPageLoadError(Exception):
    pass


class DeepLCLI:
    fr_langs: ClassVar[set[str]] = {
        "auto",
        "bg",
        "cs",
        "da",
        "de",
        "el",
        "en",
        "es",
        "et",
        "fi",
        "fr",
        "hu",
        "id",
        "it",
        "ja",
        "ko",
        "lt",
        "lv",
        "nl",
        "pl",
        "pt",
        "ro",
        "ru",
        "sk",
        "sl",
        "sv",
        "tr",
        "uk",
        "zh",
    }
    to_langs = fr_langs | {"en-US", "en-GB", "nb", "pt-BR"} - {"auto"}

    def __init__(
        self,
        fr_lang: str,
        to_lang: str,
        timeout: int = 15000,
        *,
        use_dom_submit: bool = False,
    ) -> None:
        if fr_lang not in self.fr_langs:
            raise DeepLCLIError(f"{fr_lang!r} is not valid language. Valid language:\n" + repr(self.fr_langs))
        if to_lang not in self.to_langs:
            raise DeepLCLIError(f"{to_lang!r} is not valid language. Valid language:\n" + repr(self.to_langs))

        self.fr_lang = fr_lang
        self.to_lang = to_lang
        self.translated_fr_lang: str | None = None
        self.translated_to_lang: str | None = None
        self.max_length = 3000
        self.timeout = timeout
        self.use_dom_submit = use_dom_submit

    def translate(self, batch: List[str]) -> List[str]:
        batch = [self.__sanitize_script(script) for script in batch]

        # run in the current thread
        return self.__translate(batch)

    # def translate_async(self, script: str) -> Coroutine[Any, Any, str]:
    #     script = self.__sanitize_script(script)
    #
    #     return self.__translate(script)

    def __translate(self, batch: List[str]) -> List[str]:
        """Throw a request."""
        results = []

        with sync_playwright() as p:
            # Dry run
            try:
                browser = self.__get_browser(p)
            except PlaywrightError as e:
                if "Executable doesn't exist at" in e.message:
                    print("Installing browser executable. This may take some time.")  # noqa: T201
                    asyncio.get_event_loop().run_in_executor(None, install, p.chromium)
                    browser = self.__get_browser(p)
                else:
                    raise

            page = browser.new_page()
            page.set_default_timeout(self.timeout)
            for script in batch:
                # skip loading page resources for improving performance
                excluded_resources = ["image", "media", "font", "other"]
                page.route(
                    "**/*",
                    lambda route: route.abort() if route.request.resource_type in excluded_resources else route.continue_(),
                )

                url = "https://www.deepl.com/en/translator"
                if self.use_dom_submit:
                    page.goto(url)
                else:
                    script = quote(script, safe="")
                    page.goto(f"{url}#{self.fr_lang}/{self.to_lang}/{script}")

                # Wait for loading to complete
                try:
                    page.get_by_role("main")
                except PlaywrightError as e:
                    msg = f"Maybe Time limit exceeded. ({self.timeout} ms)"
                    raise DeepLCLIPageLoadError(msg) from e

                if self.use_dom_submit:
                    # banner prevents clicking on language buttons, close the banner first
                    page.click("button[data-testid=cookie-banner-lax-close-button]")
                    # select input / output language
                    page.click("button[data-testid=translator-source-lang-btn]")
                    page.click(f"button[data-testid=translator-lang-option-{self.fr_lang}]")
                    page.click("button[data-testid=translator-target-lang-btn]")
                    page.click(f"button[data-testid=translator-lang-option-{self.to_lang}]")
                    # fill in the form of translating script
                    page.fill("div[aria-labelledby=translation-source-heading]", script)

                # Wait for translation to complete
                try:
                    page.wait_for_function(
                        """
                        () => document.querySelector(
                        'd-textarea[aria-labelledby=translation-target-heading]')?.value?.length > 0
                        """,
                    )
                except PlaywrightError as e:
                    msg = f"Time limit exceeded. ({self.timeout} ms)"
                    raise DeepLCLIPageLoadError(msg) from e

                # Get information
                input_textbox = page.get_by_role("region", name="Source text").locator("d-textarea")
                output_textbox = page.get_by_role("region", name="Translation results").locator("d-textarea")

                self.translated_fr_lang = str(input_textbox.get_attribute("lang")).split("-")[0]
                self.translated_to_lang = str(output_textbox.get_attribute("lang")).split("-")[0]

                res = str((output_textbox.all_inner_texts())[0])
                # the extra \n is generated by <p> tag because every line is covered by it
                res = res.replace("\n\n", "\n")
                results.append(res.rstrip("\n"))
            browser.close()
            return results

    def __sanitize_script(self, script: str) -> str:
        """Check command line args and stdin."""
        script = script.rstrip("\n")

        if self.max_length is not None and len(script) > self.max_length:
            msg = f"Limit of script is less than {self.max_length} chars (Now: {len(script)} chars)"
            raise DeepLCLIError(msg)

        if len(script) <= 0:
            msg = "Script seems to be empty."
            raise DeepLCLIError(msg)

        return script.replace("/", r"\/").replace("|", r"\|")

    def __get_browser(self, p: Playwright) -> Browser:
        """Launch browser executable and get playwright browser object."""
        return p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--single-process",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-zygote",
                "--window-size=1920,1080",
            ],
        )


if __name__ == '__main__':
    deepl = DeepLCLI('uk', "ru")
    translates = deepl.translate(['нехай щастить', 'нема чого ходить'])
    print(translates)