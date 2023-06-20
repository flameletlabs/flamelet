## flamelet

A DevOps tool for remote infrastructure management.

## Getting Started

### Prerequisites

- A Unix-like operating system: macOS, Linux, BSD. On Windows: WSL2 is preferred, but cygwin or msys also mostly work.
- `bash` should be installed
- `curl` or `wget` should be installed
- `git` should be installed

### Basic Installation

Flamelet is installed by running one of the following commands in your terminal. You can install this via the command-line with either `curl`, `wget` or another similar tool.

| Method    | Command                                                                                                 |
| :-------- | :------------------------------------------------------------------------------------------------------ |
| **curl**  | `sh -c "$(curl -fsSL https://raw.githubusercontent.com/flameletlabs/flamelet/main/tools/install.sh)"` |
| **wget**  | `sh -c "$(wget -O- https://raw.githubusercontent.com/flameletlabs/flamelet/main/tools/install.sh)"`   |
| **fetch** | `sh -c "$(fetch -o - https://raw.githubusercontent.com/flameletlabs/flamelet/main/tools/install.sh)"` |
