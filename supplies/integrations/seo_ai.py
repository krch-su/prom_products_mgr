from __future__ import annotations

import re
from typing import TYPE_CHECKING, List

from playwright._impl._errors import Error as PlaywrightError
from playwright.sync_api import sync_playwright, expect
from playwright_recaptcha import recaptchav3
from playwright_stealth import stealth_sync

if TYPE_CHECKING:
    from playwright.sync_api._generated import Browser, Playwright


class SEOAIError(Exception):
    pass


class SEOAIPageLoadError(Exception):
    pass


class SEOAI:

    def __init__(
        self,
        timeout: int = 15000,
    ) -> None:
        self.max_length = 1000
        self.timeout = timeout

    def translate(self, batch: List[str]) -> List[List[str]]:
        batch = [self.__sanitize_script(script) for script in batch]

        # run in the current thread
        return self.__translate(batch)

    def __translate(self, batch: List[str]) -> List[List[str]]:
        """Throw a request."""

        results = []

        with sync_playwright() as p:
            browser = self.__get_browser(p)

            page = browser.new_page()
            stealth_sync(page)
            page.set_default_timeout(self.timeout)
            for script in batch:
                # skip loading page resources for improving performance
                excluded_resources = ["image", "media", "font", "other"]
                page.route(
                    "**/*",
                    lambda route: route.abort() if route.request.resource_type in excluded_resources else route.continue_(),
                )

                with recaptchav3.SyncSolver(page) as solver:

                    url = "https://seo.ai/tools/ai-keyword-tool"
                    page.goto(url)

                    page.wait_for_selector("#inputBox")

                    print(script)
                    print(page.is_visible('#inputBox'))
                    page.locator("#inputBox").fill(script)
                    # page.evaluate("solution => document.querySelector('#inputBox').innerHTML = solution",
                    #               script)
                    print(page.locator('#inputBox').inner_html())
                    page.locator("button:has-text(\"Generate keywords\")").click()
                    # with page.expect_response(re.compile(r".*/recaptcha/api2/bframe.*")):
                    page.wait_for_selector('[id*="recaptcha-"]')
                    token = solver.solve_recaptcha()
                    print(token)
                    expect('#loadingSpinner').to_have_count(0)

                    results_block = page.locator('//*[@id="aikeywordtool"]/div/div[5]/div')

                    res = results_block.all_inner_texts()[1:]
                    results.append(res)
            browser.close()
            return results

    def __sanitize_script(self, script: str) -> str:
        """Check command line args and stdin."""
        script = script.rstrip("\n")

        if self.max_length is not None and len(script) > self.max_length:
            msg = f"Limit of script is less than {self.max_length} chars (Now: {len(script)} chars)"
            raise SEOAIError(msg)

        if len(script) <= 0:
            msg = "Script seems to be empty."
            raise SEOAIError(msg)

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
    deepl = SEOAI()
    translates = deepl.translate(['Газовый баллон Base Camp 4 season gas 220 г черный Украина'])
    print(translates)