# TradeHarbor

TradeHarbor is a comprehensive management panel designed to handle offers/products from multiple dropshipping suppliers. It allows you to create unique content (product titles, product descriptions) using ChatGPT, manage product groups, and handle keyword management. With the potential to evolve into a fully functional CRM system, TradeHarbor is built using Django, Celery, and lxml.

## Features

- **Offer Management:** Efficiently manage and synchronize offers/products from multiple dropshipping suppliers.

- **Unique Content Creation:** Integrate ChatGPT for generating unique and engaging product titles and descriptions.

- **Product Groups:** Organize products into groups for better management and categorization.

- **Keyword Management:** Efficiently handle and organize keywords for enhanced product visibility.

- **Scalable Architecture:** Built on Django and Celery for scalability, ensuring seamless growth as your project expands.

- **Flexible Data Parsing:** Utilizes lxml for flexible and efficient data parsing from diverse supplier sources.

- **Extensible Design:** Designed with future expansion in mind, making it easy to evolve into a fully functional CRM system.

- **Dependency Management:** Dependency management is handled using Poetry, ensuring clean and reliable package management.

## Prerequisites

- [Python](https://www.python.org/) (>= 3.8)
- [Poetry](https://python-poetry.org/) for dependency management

## Getting Started

1. Clone the repository:

    ```bash
    git clone https://github.com/your-username/TradeHarbor.git
    ```

2. Install dependencies:

    ```bash
    cd TradeHarbor
    poetry install
    ```

3. Apply migrations:

    ```bash
    python manage.py migrate
    ```

4. Run the development server:

    ```bash
    python manage.py runserver
    ```

5. Access TradeHarbor at [http://localhost:8000/](http://localhost:8000/)

## Usage

- Detailed instructions on how to use and configure TradeHarbor, including content creation with ChatGPT, product group management, and keyword organization, will be provided in the [documentation](docs/).

## Contributing

Contributions are welcome! For major changes, please open an issue first to discuss what you would like to change.
[pyproject.toml](pyproject.toml)
## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.