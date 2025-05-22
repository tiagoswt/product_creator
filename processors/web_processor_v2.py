"""
Enhanced web processor module for extracting data from websites.
Includes FireCrawler for advanced crawling capabilities.
"""

import os
import streamlit as st
import tempfile
import requests
import json
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from langchain_community.document_loaders import (
    WebBaseLoader,
    RecursiveUrlLoader,
    AsyncHtmlLoader,
)
from langchain_community.document_transformers import BeautifulSoupTransformer
import logging
from tqdm.auto import tqdm
import asyncio
import re


class FireCrawler:
    """
    Advanced web crawler for e-commerce sites that leverages LangChain loaders
    and provides additional filtering and processing capabilities.
    """

    def __init__(
        self,
        base_url,
        max_depth=2,
        max_pages=20,
        product_url_patterns=None,
        excluded_patterns=None,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        use_playwright=False,
        follow_links=True,
        single_page_only=False,
        respect_robots_txt=True,
        extract_product_schema=True,
        wait_time=1.0,
    ):
        """
        Initialize the FireCrawler.

        Args:
            base_url (str): The starting URL for the crawl
            max_depth (int): Maximum depth for recursive crawling
            max_pages (int): Maximum number of pages to crawl
            product_url_patterns (list): Regex patterns to identify product URLs
            excluded_patterns (list): Regex patterns for URLs to exclude
            user_agent (str): User agent to use for requests
            use_playwright (bool): Whether to use JavaScript rendering
            follow_links (bool): Whether to follow links or just scrape the base URL
            single_page_only (bool): If True, only scrape the provided URL with no crawling
            respect_robots_txt (bool): Whether to respect robots.txt
            extract_product_schema (bool): Whether to extract product schema.org data
            wait_time (float): Time to wait between requests
        """
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.product_url_patterns = product_url_patterns or []

        # Default excluded patterns
        default_excluded = [
            r".*\.(css|js|jpg|jpeg|png|gif|pdf|zip|ico)$",
            r".*/tag/.*$",
            r".*/category/.*$",
            r".*/page/.*$",
            r".*/wp-admin/.*$",
            r".*/wp-content/.*$",
            r".*/cart/.*$",
            r".*/checkout/.*$",
            r".*/my-account/.*$",
            r".*/login/.*$",
            r".*/register/.*$",
        ]

        self.excluded_patterns = (
            excluded_patterns if excluded_patterns is not None else default_excluded
        )
        self.user_agent = user_agent
        self.use_playwright = use_playwright
        self.follow_links = follow_links and not single_page_only
        self.single_page_only = single_page_only
        self.respect_robots_txt = respect_robots_txt
        self.extract_product_schema = extract_product_schema
        self.wait_time = wait_time
        self.visited_urls = set()
        self.documents = []
        self.crawl_results = {
            "total_pages": 0,
            "product_pages": 0,
            "errors": 0,
            "schema_found": 0,
        }

        # Setup headers
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }

    def is_product_url(self, url):
        """Check if the URL matches product URL patterns"""
        # Default check: if URL contains product, products, item, or items
        if not self.product_url_patterns:
            return bool(re.search(r"product|item", url, re.IGNORECASE))

        # Check against custom patterns
        for pattern in self.product_url_patterns:
            if re.search(pattern, url):
                return True
        return False

    def is_excluded_url(self, url):
        """Check if the URL matches excluded patterns"""
        for pattern in self.excluded_patterns:
            if re.search(pattern, url):
                return True
        return False

    def is_same_domain(self, url):
        """Check if the URL is from the same domain"""
        parsed_url = urlparse(url)
        return parsed_url.netloc == self.domain

    def extract_links(self, soup, current_url):
        """Extract links from a BeautifulSoup object"""
        links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            # Make relative URLs absolute
            absolute_url = urljoin(current_url, href)

            # Filter URLs
            if (
                self.is_same_domain(absolute_url)
                and not self.is_excluded_url(absolute_url)
                and absolute_url not in self.visited_urls
            ):
                links.append(absolute_url)

        return links

    def extract_product_data(self, soup):
        """Extract product schema.org data if available"""
        product_data = {}

        # Look for JSON-LD product schema
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string)
                # Handle both direct Product and Graph with Product nodes
                if isinstance(data, dict):
                    if data.get("@type") == "Product":
                        product_data = data
                        break
                    elif data.get("@graph"):
                        for item in data["@graph"]:
                            if item.get("@type") == "Product":
                                product_data = item
                                break
            except:
                continue

        # If no JSON-LD, look for microdata
        if not product_data:
            product_elem = soup.find(itemtype=re.compile(r"schema.org/Product"))
            if product_elem:
                product_data["@type"] = "Product"
                name_elem = product_elem.find(itemprop="name")
                if name_elem:
                    product_data["name"] = name_elem.text.strip()
                price_elem = product_elem.find(itemprop="price")
                if price_elem:
                    product_data["offers"] = {"price": price_elem.text.strip()}

        return product_data

    async def crawl_with_basic(self):
        """Crawl website using basic recursive crawler"""
        queue = [(self.base_url, 0)]  # (url, depth)
        progress_bar = st.progress(0)
        status_text = st.empty()

        while queue and len(self.visited_urls) < self.max_pages:
            current_url, depth = queue.pop(0)

            if current_url in self.visited_urls:
                continue

            self.visited_urls.add(current_url)
            status_text.text(f"Crawling: {current_url}")

            try:
                # Fetch and parse the page
                response = requests.get(current_url, headers=self.headers, timeout=10)
                if response.status_code != 200:
                    self.crawl_results["errors"] += 1
                    continue

                soup = BeautifulSoup(response.text, "html.parser")

                # Create document
                doc_content = soup.get_text(separator="\n", strip=True)
                is_product = self.is_product_url(current_url)

                if is_product:
                    self.crawl_results["product_pages"] += 1

                    # Extract product schema if requested
                    if self.extract_product_schema:
                        product_data = self.extract_product_data(soup)
                        if product_data:
                            self.crawl_results["schema_found"] += 1
                            doc_content += (
                                f"\n\nPRODUCT SCHEMA: {json.dumps(product_data)}"
                            )

                self.documents.append(
                    {
                        "page_content": doc_content,
                        "metadata": {"source": current_url, "is_product": is_product},
                    }
                )

                self.crawl_results["total_pages"] += 1

                # Follow links if requested and not at max depth
                if self.follow_links and depth < self.max_depth:
                    links = self.extract_links(soup, current_url)
                    for link in links:
                        queue.append((link, depth + 1))

                # Update progress
                progress = min(len(self.visited_urls) / self.max_pages, 1.0)
                progress_bar.progress(progress)

                # Respect rate limiting
                await asyncio.sleep(self.wait_time)

            except Exception as e:
                logging.error(f"Error crawling {current_url}: {str(e)}")
                self.crawl_results["errors"] += 1

        progress_bar.progress(1.0)
        status_text.text(
            f"Crawling completed: {self.crawl_results['total_pages']} pages crawled"
        )

    async def crawl_with_langchain(self):
        """Crawl website using LangChain loaders"""
        status_text = st.empty()
        status_text.text(f"Setting up crawler for: {self.base_url}")

        try:
            if self.use_playwright:
                # For sites that require JavaScript, we need a more direct approach
                import requests
                from playwright.async_api import async_playwright

                status_text.text(
                    f"Using Playwright to render JavaScript on: {self.base_url}"
                )

                try:
                    # Initialize Playwright
                    async with async_playwright() as p:
                        # Launch a browser
                        browser = await p.chromium.launch(headless=True)

                        # Create a context with specific user agent
                        context = await browser.new_context(
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                            viewport={"width": 1280, "height": 720},
                        )

                        # Create a page and navigate to the URL
                        page = await context.new_page()

                        # Sometimes we need to accept cookies
                        status_text.text(
                            f"Loading page and handling any popups: {self.base_url}"
                        )
                        await page.goto(
                            self.base_url, wait_until="networkidle", timeout=30000
                        )

                        # Wait a bit more for any dynamic content
                        await asyncio.sleep(self.wait_time)

                        # Try to find and click cookie consent buttons
                        cookie_button_selectors = [
                            "button:has-text('Accept')",
                            "button:has-text('Accept All')",
                            "button:has-text('I Accept')",
                            "button:has-text('Agree')",
                            "button:has-text('Accept Cookies')",
                            "button:has-text('Allow')",
                            "button:has-text('Allow All')",
                            "[id*='cookie'] button",
                            "[class*='cookie'] button",
                            "[id*='consent'] button",
                            "[class*='consent'] button",
                            "[id*='gdpr'] button",
                            "[class*='gdpr'] button",
                        ]

                        for selector in cookie_button_selectors:
                            try:
                                if await page.locator(selector).count() > 0:
                                    await page.locator(selector).first.click()
                                    status_text.text("Clicked cookie consent button")
                                    # Wait for the page to stabilize after click
                                    await asyncio.sleep(1)
                                    break
                            except Exception:
                                continue

                        # Get the content after JS has executed
                        content = await page.content()
                        await browser.close()

                        # Create a document from the rendered HTML
                        soup = BeautifulSoup(content, "html.parser")

                        # Clean up the content a bit
                        for s in soup.select("script, style, nav, footer, header"):
                            s.extract()

                        # Create a document
                        from langchain_core.documents import Document

                        doc = Document(
                            page_content=soup.get_text(separator="\n", strip=True),
                            metadata={
                                "source": self.base_url,
                                "is_product": self.is_product_url(self.base_url),
                                "html_content": str(soup),  # Store HTML for debugging
                            },
                        )

                        # Try to extract product data
                        if self.extract_product_schema and self.is_product_url(
                            self.base_url
                        ):
                            product_data = self.extract_product_data(soup)
                            if product_data:
                                self.crawl_results["schema_found"] += 1
                                doc.metadata["product_data"] = product_data

                        # Store results
                        self.documents = [doc]
                        self.crawl_results["total_pages"] = 1
                        if self.is_product_url(self.base_url):
                            self.crawl_results["product_pages"] = 1

                except Exception as e:
                    status_text.error(f"Error using Playwright: {str(e)}")
                    st.warning("Falling back to standard HTML loader")

                    # Fallback to AsyncHtmlLoader
                    loader = AsyncHtmlLoader(
                        [self.base_url], verify_ssl=False, requests_per_second=1
                    )
                    docs = await loader.aload()

                    # Apply BS transformer to extract useful content
                    bs_transformer = BeautifulSoupTransformer()
                    self.documents = bs_transformer.transform_documents(docs)

            elif not self.follow_links:
                # Just load the base URL
                status_text.text(f"Loading single page: {self.base_url}")
                loader = WebBaseLoader(
                    web_paths=[self.base_url], header_template=self.headers
                )
                documents = loader.load()

                # Transform documents to extract more structured data
                bs_transformer = BeautifulSoupTransformer()
                self.documents = bs_transformer.transform_documents(documents)

            else:
                # Use recursive crawler
                status_text.text(
                    f"Setting up recursive crawler starting at: {self.base_url}"
                )
                loader = RecursiveUrlLoader(
                    url=self.base_url,
                    max_depth=self.max_depth,
                    extractor=lambda x: BeautifulSoup(x, "html.parser").text,
                    prevent_outside=True,
                    use_async=True,
                    timeout=30,
                    headers=self.headers,
                )
                documents = loader.load()

                # Limit to max_pages
                documents = documents[: self.max_pages]

                # Transform documents to extract more structured data
                bs_transformer = BeautifulSoupTransformer()
                self.documents = bs_transformer.transform_documents(documents)

            # Process all documents
            status_text.text(f"Processing {len(self.documents)} documents...")
            for i, doc in enumerate(self.documents):
                try:
                    # Update URL in metadata if not present
                    if not doc.metadata.get("source"):
                        doc.metadata["source"] = f"{self.base_url}/page_{i}"

                    # Check if it's a product page
                    is_product = self.is_product_url(doc.metadata["source"])
                    doc.metadata["is_product"] = is_product

                    if is_product:
                        self.crawl_results["product_pages"] += 1

                        # Extract product schema for product pages
                        if (
                            self.extract_product_schema
                            and "html_content" not in doc.metadata
                        ):
                            try:
                                soup = BeautifulSoup(doc.page_content, "html.parser")
                                product_data = self.extract_product_data(soup)
                                if product_data:
                                    self.crawl_results["schema_found"] += 1
                                    doc.metadata["product_data"] = product_data
                            except:
                                pass

                except Exception as e:
                    logging.error(f"Error processing document: {str(e)}")
                    self.crawl_results["errors"] += 1

            self.crawl_results["total_pages"] = len(self.documents)

            status_text.text(
                f"Crawling completed: {len(self.documents)} pages processed"
            )

        except Exception as e:
            logging.error(f"Error in langchain crawling: {str(e)}")
            status_text.text(f"Error crawling: {str(e)}")
            self.crawl_results["errors"] += 1

    async def crawl(self):
        """Main crawl method that selects appropriate crawler"""
        # Special handling for Douglas.pt
        if "douglas.pt" in self.base_url:
            st.info("Detected Douglas.pt website - using simplified headers")
            # Simplify headers for Douglas.pt to avoid the "headers too large" error
            self.headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }

        if self.single_page_only:
            # In single page mode, force using WebBaseLoader for just one page
            st.info(f"Single page mode: Scraping only {self.base_url}")

            try:
                # For Douglas.pt, use a special approach to bypass headers issue
                if "douglas.pt" in self.base_url:
                    try:
                        # First attempt with minimal headers
                        response = requests.get(
                            self.base_url,
                            headers=self.headers,
                            timeout=10,
                            allow_redirects=True,
                        )

                        if response.status_code != 200:
                            st.warning(
                                f"Got status code {response.status_code} from Douglas.pt. Trying alternative approach..."
                            )
                            # Second attempt with no cookies and even more minimal headers
                            headers = {"User-Agent": "Mozilla/5.0"}
                            response = requests.get(
                                self.base_url,
                                headers=headers,
                                timeout=10,
                                allow_redirects=True,
                            )

                        # If we got a response, parse it manually
                        if response.status_code == 200:
                            html_content = response.text
                            soup = BeautifulSoup(html_content, "html.parser")

                            # Extract and create document manually
                            text_content = soup.get_text(separator="\n", strip=True)

                            # Try to extract product data
                            product_data = {}
                            if self.extract_product_schema:
                                product_data = self.extract_product_data(soup)
                                if product_data:
                                    self.crawl_results["schema_found"] = 1

                            # Create a document manually
                            from langchain_core.documents import Document

                            doc = Document(
                                page_content=text_content,
                                metadata={
                                    "source": self.base_url,
                                    "is_product": True,
                                    "product_data": (
                                        product_data if product_data else None
                                    ),
                                },
                            )

                            self.documents = [doc]
                            self.crawl_results["total_pages"] = 1
                            self.crawl_results["product_pages"] = 1
                            return
                        else:
                            st.error(
                                f"Failed to access Douglas.pt: Status code {response.status_code}"
                            )

                    except Exception as e:
                        st.error(f"Error accessing Douglas.pt: {str(e)}")
                        # Continue with normal approach as fallback

                # Standard approach for other sites
                # Use AsyncHtmlLoader for JavaScript rendering if needed
                if self.use_playwright:
                    loader = AsyncHtmlLoader([self.base_url], verify_ssl=False)
                    docs = await loader.aload()
                else:
                    # Use WebBaseLoader for simpler pages
                    loader = WebBaseLoader(
                        [self.base_url], header_template=self.headers
                    )
                    docs = loader.load()

                # Process the single page
                bs_transformer = BeautifulSoupTransformer()
                processed_docs = bs_transformer.transform_documents(docs)

                # Store the results
                self.documents = processed_docs
                self.crawl_results["total_pages"] = 1

                # Check if this is a product page
                if self.is_product_url(self.base_url):
                    self.crawl_results["product_pages"] = 1

                    # Try to extract product data if needed
                    if self.extract_product_schema and processed_docs:
                        for doc in processed_docs:
                            try:
                                soup = BeautifulSoup(doc.page_content, "html.parser")
                                product_data = self.extract_product_data(soup)
                                if product_data:
                                    self.crawl_results["schema_found"] = 1
                                    doc.metadata["product_data"] = product_data
                            except Exception as e:
                                st.warning(f"Error extracting product data: {str(e)}")

            except Exception as e:
                st.error(f"Error in single page mode: {str(e)}")
                self.crawl_results["errors"] = 1

        elif self.follow_links and not self.use_playwright:
            # For sites that need deeper crawling, use the basic crawler
            # which gives more control over the crawling process
            await self.crawl_with_basic()
        else:
            # For simple cases or when using Playwright, use LangChain loaders
            await self.crawl_with_langchain()

    def get_documents(self):
        """Get the documents loaded during crawling"""
        return self.documents

    def get_stats(self):
        """Get crawling statistics"""
        return self.crawl_results

    def get_text(self):
        """Get all text content extracted during crawling"""
        combined_text = f"--- WEBSITE DATA FROM {self.base_url} ---\n\n"

        # Add crawl stats
        combined_text += f"Crawl Statistics:\n"
        combined_text += f"Total Pages: {self.crawl_results['total_pages']}\n"
        combined_text += f"Product Pages: {self.crawl_results['product_pages']}\n"
        combined_text += f"Pages with Schema: {self.crawl_results['schema_found']}\n"
        combined_text += f"Errors: {self.crawl_results['errors']}\n\n"

        # Add page content
        for i, doc in enumerate(self.documents):
            url = doc.metadata.get("source", f"Page {i+1}")
            is_product = doc.metadata.get("is_product", False)
            page_type = "PRODUCT PAGE" if is_product else "PAGE"

            combined_text += f"--- {page_type}: {url} ---\n"

            # Add product data if available
            if is_product and "product_data" in doc.metadata:
                combined_text += (
                    f"PRODUCT DATA: {json.dumps(doc.metadata['product_data'])}\n\n"
                )

            # Add page content
            combined_text += doc.page_content + "\n\n"
            combined_text += "-" * 80 + "\n\n"

        return combined_text


def detect_ecommerce_type(url):
    """
    Attempts to identify the type of e-commerce site to optimize crawling

    Args:
        url (str): The URL to analyze

    Returns:
        dict: Configuration parameters for FireCrawler
    """
    # Default configuration to use if detection fails
    default_config = {
        "platform": "unknown",
        "max_depth": 2,
        "max_pages": 10,
        "use_playwright": False,
        "product_url_patterns": [],
    }

    try:
        # Use a shorter timeout and more robust headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }

        # Use a shorter timeout for the initial check
        st.info(f"Checking website structure: {url}")
        response = requests.get(url, timeout=5, headers=headers)
        html = response.text.lower()

        config = {
            "max_depth": 2,
            "max_pages": 20,
            "use_playwright": False,
            "product_url_patterns": [],
        }

        # Detect platform by page source and structure
        if "shopify" in html or "shopify.com" in html:
            config["platform"] = "shopify"
            config["product_url_patterns"] = [r"/products/"]
            config["max_depth"] = 3

        elif "woocommerce" in html or "wp-content" in html:
            config["platform"] = "woocommerce"
            config["product_url_patterns"] = [r"/product/"]
            config["max_depth"] = 3

        elif "magento" in html:
            config["platform"] = "magento"
            config["max_depth"] = 2
            config["use_playwright"] = True

        elif "bigcommerce" in html:
            config["platform"] = "bigcommerce"
            config["product_url_patterns"] = [r"/products/"]

        elif "prestashop" in html:
            config["platform"] = "prestashop"

        # Check for heavy JS usage that might require Playwright
        if any(x in html for x in ["vue", "react", "angular", "axios", "fetch("]):
            config["use_playwright"] = True

        # Try to detect product URL patterns if none were found
        if not config["product_url_patterns"]:
            # Look for common product patterns in the HTML
            common_patterns = [
                r"/product/",
                r"/products/",
                r"/item/",
                r"/items/",
                r"/p/",
            ]
            for pattern in common_patterns:
                if pattern in html:
                    config["product_url_patterns"].append(pattern)

        # Douglas.pt specific pattern (for your example)
        if "douglas.pt" in url:
            config["platform"] = "douglas"
            config["product_url_patterns"] = [r"/product/"]
            config["max_depth"] = 2
            config["max_pages"] = 15
            config["use_playwright"] = True

        return config

    except requests.exceptions.Timeout:
        # Special handling for timeout errors
        st.warning(f"Website detection timed out. Using default settings.")
        logging.warning(f"Timeout while detecting e-commerce type for {url}")

        # Try to determine configuration from URL structure instead
        if "shopify" in url:
            default_config["platform"] = "shopify"
            default_config["product_url_patterns"] = [r"/products/"]
        elif "woocommerce" in url or "wp-content" in url or "/product/" in url:
            default_config["platform"] = "woocommerce"
            default_config["product_url_patterns"] = [r"/product/"]

        # Douglas.pt specific pattern (for your example)
        if "douglas.pt" in url:
            default_config["platform"] = "douglas"
            default_config["product_url_patterns"] = [r"/product/"]
            default_config["max_depth"] = 2
            default_config["max_pages"] = 15
            default_config["use_playwright"] = True

        return default_config

    except Exception as e:
        # Default configuration if detection fails for any other reason
        st.warning(f"Website detection failed: {str(e)}. Using default settings.")
        logging.error(f"Error detecting e-commerce type: {str(e)}")
        return default_config


async def extract_website_data(website_url, advanced_options=None):
    """
    Extract text data from website using FireCrawler

    Args:
        website_url (str): URL of the website to extract data from
        advanced_options (dict): Optional configuration parameters for FireCrawler

    Returns:
        str: Text content from the website
    """
    if not website_url:
        return None

    try:
        # Add single page mode as a prominent option at the top level
        single_page_only = st.checkbox(
            "Single page mode (only scrape the URL you entered, no crawling)",
            value=True,  # Default to enabled for simplicity
            help="Enable this to only extract data from the exact URL - faster and more focused",
        )

        # For sites that likely need JavaScript, auto-enable JavaScript rendering
        js_required = False
        for domain in ["lancome", "sephora", "ulta", "macys", "nordstrom"]:
            if domain in website_url:
                js_required = True
                st.info(
                    f"Detected {domain} website, which likely requires JavaScript rendering"
                )
                break

        # Add option to show raw extracted data
        show_raw_data = st.checkbox(
            "Show raw extracted data",
            value=True,
            help="Display the raw data extracted from the website for inspection",
        )

        # Force JavaScript rendering for sites that require it
        use_playwright = st.checkbox(
            "Enable JavaScript rendering (required for many modern websites)",
            value=js_required,
            help="Use this for sites that show 'Enable JavaScript' messages or have dynamic content",
        )

        with st.expander("Advanced Crawler Configuration", expanded=False):
            st.info(
                "FireCrawl will automatically detect the best settings for the website."
            )

            # Allow manual overrides if desired
            if advanced_options is None:
                # Detect e-commerce type and get default configuration
                with st.spinner("Detecting website type..."):
                    try:
                        default_config = detect_ecommerce_type(website_url)
                        if "platform" in default_config:
                            st.success(
                                f"Detected platform: {default_config['platform']}"
                            )
                    except Exception as e:
                        st.warning(f"Could not detect website type: {str(e)}")
                        default_config = {
                            "platform": "unknown",
                            "max_depth": 2,
                            "max_pages": 10,
                            "use_playwright": use_playwright,
                        }

                # Advanced options are only relevant if not in single page mode
                col1, col2 = st.columns(2)
                with col1:
                    max_depth = st.number_input(
                        "Maximum crawl depth",
                        min_value=1,
                        max_value=5,
                        value=default_config.get("max_depth", 2),
                        disabled=single_page_only,
                    )
                    max_pages = st.number_input(
                        "Maximum pages to crawl",
                        min_value=1,
                        max_value=50,
                        value=default_config.get("max_pages", 20),
                        disabled=single_page_only,
                    )

                with col2:
                    wait_time = st.number_input(
                        "Wait time (seconds)",
                        min_value=0.0,
                        max_value=10.0,
                        value=2.0,
                        step=0.5,
                        help="Time to wait for JavaScript content to load",
                    )
                    extract_schema = st.checkbox("Extract product schema", value=True)

                advanced_options = {
                    "single_page_only": single_page_only,
                    "show_raw_data": show_raw_data,
                    "max_depth": max_depth,
                    "max_pages": max_pages,
                    "use_playwright": use_playwright,
                    "wait_time": wait_time,
                    "extract_product_schema": extract_schema,
                    "product_url_patterns": default_config.get(
                        "product_url_patterns", []
                    ),
                }
            else:
                # Override the single_page_only and show_raw_data settings in existing advanced_options
                advanced_options["single_page_only"] = single_page_only
                advanced_options["show_raw_data"] = show_raw_data
                advanced_options["use_playwright"] = use_playwright

        if advanced_options is None:
            # Use basic detection with fallback
            try:
                advanced_options = detect_ecommerce_type(website_url)
                advanced_options["single_page_only"] = single_page_only
                advanced_options["show_raw_data"] = show_raw_data
            except Exception:
                advanced_options = {
                    "max_depth": 2,
                    "max_pages": 10,
                    "use_playwright": False,
                    "single_page_only": single_page_only,
                    "show_raw_data": show_raw_data,
                }

        # Initialize and run the FireCrawler
        crawler = FireCrawler(
            base_url=website_url,
            max_depth=advanced_options.get("max_depth", 2),
            max_pages=advanced_options.get("max_pages", 20),
            use_playwright=advanced_options.get("use_playwright", False),
            single_page_only=advanced_options.get("single_page_only", False),
            product_url_patterns=advanced_options.get("product_url_patterns", []),
            extract_product_schema=advanced_options.get("extract_product_schema", True),
            wait_time=advanced_options.get("wait_time", 1.0),
        )

        # Start the crawling process with timeout handling
        with st.spinner(f"Crawling {website_url} - this may take a few moments..."):
            try:
                # Set a reasonable timeout for the entire crawl process
                await asyncio.wait_for(crawler.crawl(), timeout=120)
            except asyncio.TimeoutError:
                st.warning("Crawling timed out. Using partial results.")

        # Display raw data if requested
        if advanced_options.get("show_raw_data", False):
            with st.expander("Raw Extracted Data", expanded=True):
                st.subheader("Crawl Statistics")
                st.json(crawler.get_stats())

                st.subheader("Extracted Documents")
                for i, doc in enumerate(crawler.get_documents()):
                    with st.expander(
                        f"Document {i+1}: {doc.metadata.get('source', 'Unknown URL')}",
                        expanded=i == 0,
                    ):
                        st.markdown("#### Metadata")
                        st.json(doc.metadata)

                        # Display product data if available
                        if (
                            "product_data" in doc.metadata
                            and doc.metadata["product_data"]
                        ):
                            st.markdown("#### Product Data")
                            st.json(doc.metadata["product_data"])

                        st.markdown("#### Content")
                        content_preview = (
                            doc.page_content[:1000] + "..."
                            if len(doc.page_content) > 1000
                            else doc.page_content
                        )
                        st.text_area("Content Preview", content_preview, height=300)

                        # Add option to copy full content
                        if len(doc.page_content) > 1000:
                            st.download_button(
                                "Download Full Content",
                                doc.page_content,
                                file_name=f"document_{i+1}_content.txt",
                                mime="text/plain",
                            )

        # Get the final text output
        return crawler.get_text()

    except Exception as e:
        st.error(f"Error loading website content: {e}")
        # Fallback to simpler extraction if the advanced crawler fails
        try:
            st.info("Attempting simplified extraction...")
            return extract_website_data_legacy(website_url)
        except Exception as fallback_error:
            st.error(f"Simplified extraction also failed: {fallback_error}")
            return None

        # Start the crawling process with timeout handling
        with st.spinner(f"Crawling {website_url} - this may take a few moments..."):
            try:
                # Set a reasonable timeout for the entire crawl process
                await asyncio.wait_for(crawler.crawl(), timeout=120)
            except asyncio.TimeoutError:
                st.warning("Crawling timed out. Using partial results.")

        # Get the final text output
        return crawler.get_text()

    except Exception as e:
        st.error(f"Error loading website content: {e}")
        # Fallback to simpler extraction if the advanced crawler fails
        try:
            st.info("Attempting simplified extraction...")
            return extract_website_data_legacy(website_url)
        except Exception as fallback_error:
            st.error(f"Simplified extraction also failed: {fallback_error}")
            return None


def extract_website_data_sync(website_url, advanced_options=None):
    """
    Synchronous wrapper for extract_website_data
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        # Add timeout handling for the whole process
        result = None
        try:
            result = loop.run_until_complete(
                asyncio.wait_for(
                    extract_website_data(website_url, advanced_options),
                    timeout=180,  # 3 minutes max total time
                )
            )
        except asyncio.TimeoutError:
            st.warning(
                "Website crawling timed out. Falling back to simpler extraction."
            )
            try:
                # Try the legacy method as fallback
                result = extract_website_data_legacy(website_url)
            except Exception as e:
                st.error(f"Fallback extraction also failed: {str(e)}")
        return result
    except Exception as e:
        st.error(f"Error in website crawling: {str(e)}")
        # Try the legacy method as a last resort
        try:
            return extract_website_data_legacy(website_url)
        except:
            pass
        return None
    finally:
        loop.close()


# Original extract_website_data function for backward compatibility
def extract_website_data_legacy(website_url):
    """
    Original extract_website_data function for backward compatibility
    """
    if not website_url:
        return None

    try:
        loader = WebBaseLoader(website_url)
        docs = loader.load()

        website_text = f"--- WEBSITE DATA FROM {website_url} ---\n"
        for doc in docs:
            website_text += doc.page_content

        return website_text
    except Exception as e:
        st.error(f"Error loading website content: {e}")
        return None
