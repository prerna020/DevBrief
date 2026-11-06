# devbrief-cli

The command-line client for DevBrief, an automated
code review tool. Review your local diffs from the terminal, backed by the same
AI review engine used by DevBrief's GitHub App.

## Installation

```sh
pip install -e ./packages/devbrief-core -e ./apps/cli
```

This installs the `devbrief` command.

## Authentication

Before using `devbrief review`, authenticate with a DevBrief API key (create one on your DevBrief
dashboard's API keys page):

```sh
devbrief auth
```

This prompts for your API key, validates it against your DevBrief instance, and saves it to the
platform-specific config file shown below. On POSIX the file is written with restricted
(`0600`) permissions; on Windows it lives under your already-private `%APPDATA%`.

| OS | Config file |
| --- | --- |
| Linux | `~/.config/devbrief/config.toml` |
| macOS | `~/Library/Application Support/devbrief/config.toml` |
| Windows | `%APPDATA%\devbrief\config.toml` |

The directory is created for you on first run, so you never need to mkdir by hand.

## Usage

```sh
# Review currently staged changes
devbrief review --staged

# Review uncommitted changes (staged + unstaged)
devbrief review --uncommitted

# Review the last commit
devbrief review --committed

# Review a diff from a file
devbrief review --diff path/to.diff

# Include untracked files alongside any of the above
devbrief review --staged --include-untracked
```

## Configuration

`devbrief auth` manages the platform-specific config file for you (see the table above for the
exact location per OS). To point the CLI at a self-hosted `ai-engine` instance instead of
the default (`https://devbrief-ai-engine.onrender.com`), edit the `[api] url` value in that
file, or set it before running `devbrief auth`:

```toml
[api]
url = "https://your-devbrief-instance.example.com"
api_key = "your-api-key"
```

