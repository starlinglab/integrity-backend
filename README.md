# Starling Integrity Backend <!-- omit in toc -->

- [Overview](#overview)
- [Configuration](#configuration)
- [Development](#development)
  - [Setup](#setup)
  - [Code style and formatting](#code-style-and-formatting)
  - [Dockerized Debian environment](#dockerized-debian-environment)
  - [Specifying custom assertions](#specifying-custom-assertions)
- [License](#license)

## Overview

The Starling Integrity Backend ingests ZIPs from the filesystem and operates on them for archival and preservation in various ways.

It depends on a binary of Adobe's `claim_tool`, which is planned to be open-sourced.

Other required binaries:
- `ots` from [opentimestamps-client](https://github.com/opentimestamps/opentimestamps-client)
- `ipfs` from [ipfs.io](https://ipfs.io)

## Configuration

The server is configured via environment variables and a JSON file with per-organization configuration.

See [config.example.json](./integritybackend/config.example.json) for an example of a valid organization configuration.

See [config.py](./integritybackend/config.py) for the available variables and some notes about each. In development, you can use a local `.env` file setting environment variables. See `.env.example` for an example.

Most importantly, you will need to provide:
* `CLAIM_TOOL_PATH`: A path to a fully working `claim_tool` binary. The server should have permissions to execute it, and it should be correctly configured with its keys.
* `IMAGES_DIR`: A path to a directory to store images. The server will need write access to this directory. This will be the persistent storage for the received images with their attestations.
* `ISCN_SERVER`: The instance of the ISCN server to send registration requests to. Typically, this will be `http://localhost:3000` if you are using the sample server at https://github.com/likecoin/iscn-js/tree/master/sample/server in its default configuration.

## Development

### Setup

This is a Python3 project.  We use `pipenv` to manage dependencies and the Python environment (this is like `npm` or `bundler`, but for Python). To install `pipenv` on Mac:
```bash
brew install pipenv
```

See https://github.com/pypa/pipenv#installation for installation instructions in other systems.

The [Pipfile](./Pipfile) list all our dependencies. To install them:
 ```
 pipenv install
 ```

 To install both development and default dependencies:
 ```
 pipenv install --dev
 ```

To get a shell within the Python environment for this project:
```
pipenv shell
```
This will log you into the virtualenv that pipenv has created for this environment.

See https://pipenv.pypa.io/en/latest/ for more detailed `pipenv` documentation.

To run the tests:
```
pipenv run pytest
```

### Code style and formatting

We follow [PEP8](https://www.python.org/dev/peps/pep-0008/) style guidelines, and delegate code style issues to automated tools.

We use [black](https://black.readthedocs.io/) with the default configuration for autoformatting.

To auto-format the entire codebase:
```
pipenv run autoformat
```

To auto-format just one file:
```
pipenv run black path/to/your/file.py
```

### Dockerized Debian environment

If you need to run the `claim-tool` binary in a Debian environment and don't have one on your machine, you can use the provided `docker-compose.yml` (and `Dockerfile`).

To get a shell inside the container:
```
docker-compose run --service-ports api bash
```

Once inside the container, run the usual commands (`pipenv install`, etc). You will also need a `claim_tool` binary inside the container (you can use `docker cp` to copy it into the container), as well as a directory for image storage.

### Specifying custom assertions

If you want to create a claim with manually created assertions, specify a dictionary where the key is the SHA-256 of the parent file, and the value is a list of custom assertions, then specify the path to your dictionary file in the `CUSTOM_ASSERTIONS_DICTIONARY` environment variable in your local `.env` file.

See [custom-assertions.example.json](custom-assertions.example.json) for an example.

## License

See [LICENSE](LICENSE).
