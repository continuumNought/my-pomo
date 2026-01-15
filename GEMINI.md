# My-Pomo - A Free and Open-Source Pomodoro Timer

This project is a simple, free, and open-source Pomodoro timer implemented using Python and the Textual TUI (Text User Interface) framework. It aims to provide a straightforward Pomodoro experience without the limitations of freemium models.

## Features

*   **Pomodoro Sequence:** Follows a standard Pomodoro sequence of 25 minutes work, 5 minutes short break, 25 minutes work, 10 minutes long break, repeating four times.
*   **Text User Interface (TUI):** A clean and interactive command-line interface powered by Textual.

## Setup and Installation

To get started with My-Pomo, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/my-pomo.git
    cd my-pomo
    ```
    *(Note: Replace `https://github.com/your-username/my-pomo.git` with the actual repository URL if this project is hosted elsewhere.)*

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

To run the Pomodoro timer, ensure your virtual environment is active (if you created one) and execute the main Python script:

```bash
python3 main.py
```

The timer will start automatically, displaying the current phase (Pomodoro, Short Break, Long Break) and the remaining time. The application will exit after completing the defined Pomodoro sequence.

## Contributing

Contributions are welcome! If you have suggestions for improvements or new features, please feel free to open an issue or submit a pull request.

## License

This project is licensed under the [Your Chosen License, e.g., MIT License]. See the `LICENSE` file for more details.
