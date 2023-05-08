# Starling Integrity Backend <!-- omit in toc -->

- [Overview](#overview)
- [Configuration](#configuration)
- [Architecture](#architecture)
  - [Actions](#actions)
    - [`archive`](#archive)
- [Development](#development)
  - [Setup](#setup)
  - [Code style and formatting](#code-style-and-formatting)
- [License](#license)

## Overview

The Starling Integrity Backend ingests data bundles from the filesystem and operates on them for authenticated archival.

## Configuration

The server is configured via environment variables and a JSON file with per-organization configuration.

See [config.example.json](./integritybackend/config.example.json) for an example of a valid organization configuration.

Environment variables are set in a `.env` file. See `.env.example` for an example. Available variables are documented below.

| Env Var                  | Description                                                                                                                                      | Required           |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------ |
| `C2PA_CERT_STORE`        | Path to a dir of cert and key files for C2PA                                                                                                     | For C2PA           |
| `C2PATOOL_PATH`          | Path to executable `c2patool` [binary](https://github.com/contentauth/c2patool/releases).                                                        | For C2PA           |
| `INTERNAL_ASSET_STORE`   | Local dir for storing internal assets, must exist                                                                                                | Yes                |
| `IPFS_CLIENT_PATH`       | Path to a IPFS/Kubo CLI [binary](https://github.com/ipfs/kubo)                                                                                   | Yes                |
| `ISCN_SERVER`            | ISCN server for registration. The [sample server](https://github.com/likecoin/iscn-js/tree/master/sample/server) runs at `http://localhost:3000` | For ISCN           |
| `KEY_STORE`              | Path to a dir where AES keys will be stored                                                                                                      | Yes                |
| `NUMBERS_API_KEY`        | API key for Numbers API                                                                                                                          | For Numbers        |
| `ORG_CONFIG_JSON`        | Path to organization config, see above                                                                                                           | Yes                |
| `OTS_CLIENT_PATH`        | Path to [opentimestamps-client](https://github.com/opentimestamps/opentimestamps-client)                                                         | For OpenTimestamps |
| `SHARED_FILE_SYSTEM`     | The output of actions are stored here to be shared with third-parties, must exist                                                                | Yes                |
| `WEB3_STORAGE_API_TOKEN` | API token for [web3.storage](https://web3.storage/)                                                                                              | Not currently used |


## Architecture

Data generally enters the Integrity Backend via an [Integrity Preprocessor](https://github.com/starlinglab/integrity-preprocessor). Preprocessors handle most input-specific data processing, such as root-of-trust signature validation and metadata extraction. The Integrity Backend receives ZIP files in a set of watched folders, and proceeds to processing them according to a configuration file.

The configuration file (different from `.env` file) is currently generated via a Google Spreadsheet manually curated by Starling Lab, which specifies how each `organization:collection` is assigned a set of processing `actions` alongside processing `params`. An example of these files is included [here](./config.example.json). Each time this file changes, the server must be restarted for internal states to update.

A ZIP file entering the Integrity Backend, called `inputBundle`, is dropped into a folder associated with a particular `organization:collection`, and must adhere to a specific standard. It is a ZIP file containing three files, named as follow:

```
sha256(inputBundle).zip
    sha256(content).ext
    sha256(content)-meta-content.json
    sha256(content)-meta-recorder.json
```

It is important that the ZIP file itself is named `sha256(inputBundle)`, as that ensures any change in the file content will be treated as a new asset by the data pipeline. This standardized naming is validated by the pipeline.

Examples of the `meta-content` and `meta-recorder` files are included [here](https://github.com/starlinglab/integrity-schema/tree/main/integrity-backend).

After the `inputBundle` is accepted into the data processing queue, actions assigned to the `organization:collection` will trigger.

### Actions

See [actions.py](https://github.com/starlinglab/integrity-backend/blob/main/integritybackend/actions.py).

#### `archive`

The `archive` action signs and registers the `inputBundle` onto several L1s according to the following procedure. This adds authenticity data in the archived bundles, and leaves cryptographic hashes on public L1s to establish proof-of-existence records.

Each file in the `inputBundle` is signed using [webrecorder/authsign](https://github.com/webrecorder/authsign), then registered on the Bitcoin network with [OpenTimestamps](https://opentimestamps.org). The proof files generated by these two steps are appended to the cloned `inputBundle`:

```
sha256(archive).zip
    sha256(content).ext
    sha256(content)-meta-content.json
    sha256(content)-meta-recorder.json
    proofs/
        sha256(content).ext.authsign
        sha256(content)-meta-content.json.authsign
        sha256(content)-meta-recorder.json.authsign
        sha256(content).ext.ots
        sha256(content)-meta-content.json.ots
        sha256(content)-meta-recorder.json.ots
```

The new ZIP generated is referred to as the _archive_. The archive is then encrypted using `aes-256-cbc` with a key that is generated per `organization:collection`. The encrypted file is referred to as the _encrypted archive_, and it is usually stored on centralized storage and/or decentralized storage networks. The provisioning of access (i.e. the availability of the file and sharing of the AES key) are not handled by the Integrity Backend.

At this stage, three files are hashed:

1. `content.ext`: the original content file
2. `archive.zip`: the archive file
3. `encrypt(archive.zip)`: the encrypted archive file

Each file is hashed using `md5`, `sha256`, `cidv1`, resulting in nine cryptogaphic hashes, that are then registered to L1s alongside metadata. The specific metadata that are included in the L1 registration records are fields in `meta-content` outside of the `private` JSON block. At the moment, registration is recorded on three L1s:

- Numbers using Numbers Protocol ([explorer](https://mainnet.num.network))
- Avalanche using Numbers Protocol (e.g. [snowtrace](https://snowtrace.io/tx/0x7d50283ee729b0fd4207f1ba7fd382284e101cdf961198c590e4d98a1b52d2f8))
- LikeCoin using ISCN (e.g. [bigdipper](https://bigdipper.live/likecoin/transactions/3A07C1671ACC4447523158473F66B82D244A221E80BD9E04962F72F5646FF584), [iscn](https://app.like.co/view/iscn:%2F%2Flikecoin-chain%2FOoOyDA_v5FGoSOOvs5w6R_ESMLGNSmiCJqWeHkdh2uE%2F1))

The pipeline can also be configured to create Custody Tokens (e.g. [snowtrace](https://snowtrace.io/token/0xcbaca316d909f60352f67bed6f2af9149bb82c1e)) per collection to publicly indicate current custody of each archive file.

When this process completes, a receipt file is generated containing all cryptographic hashes and registration records of the archive:

```json
{
  "inputBundle": {
    "sha256": "e36f4378c07e922af82f96d69fa233298a2a8c8ad97e92893a01cbc9255308e3"
  },
  "content": {
    "sha256": "33a8926cbe074d3f287cd741e8fcac9c29031cd648a7d7fb4718166784c49840",
    "md5": "31cfad4180267fe8cc3c77d63525ba2e",
    "cid": "bafybeietiruyfbs576yszlbrp7otz3w73efrpyjmlfhf3uhh673ajlooeu"
  },
  "archive": {
    "sha256": "da25233b60b65820334f6a9a0155453a276c416d6cdcef13f38cb59fe09adf71",
    "md5": "d164fff2e7fd8054678edbef0ed366e6",
    "cid": "bafybeiffc3dg5airhzia2mxtlgon2ep7cotw7vchkszcczvgaoctawqza4"
  },
  "archiveEncrypted": {
    "sha256": "1fea3d349a42308733924aa9662e7bff7fa9fd893f07a2986812ea8bc7b30fd1",
    "md5": "5b94895e0634533bcd15f756449c560c",
    "cid": "bafybeibaql4xglereb7z4lpdsxm3n3nirspjrmh4ytfeur33jfnwuvg7t4"
  },
  "registrationRecords": {
    "iscn": {
      "txHash": "48589A5FE8DC36262FB4BA5A7291B8068F50048C499B6DC25CEB1D6426F6E606",
      "iscnId": "iscn://likecoin-chain/POgpqXnFfjueFfPYGDu-baAYeYrlWt1ff90W4qb0y48/1"
    },
    "numbersProtocol": {
      "avalancheTxHash": "0xee8b163fa0783866526028290796a30fe4803ebe21bb4815719365ce594eba96",
      "assetCid": "bafybeif3ctgbmiso4oykvwj6jebyrkjxqr26bfrkesla5yr2ypgx47wgle",
      "assetTreeCid": "bafkreidxsbidpzsxmmzkarp6hcaiisxbzolvyynmzwjgndkzqbrqxrr3zu",
      "numbersTxHash": "0xaf192d98efdea2e7acc89f8a84a542b6df17bd17d750398d56f7f40b7f005612"
    }
  }
}
```

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

## License

See [LICENSE](LICENSE).
