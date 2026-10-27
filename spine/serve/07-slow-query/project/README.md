# globalbank

Global Bank's lakehouse on Databricks, built one course at a time.

## Connect

The CLI and every script find the workspace the same way, from
two environment variables:

    export DATABRICKS_HOST=https://<workspace>.cloud.databricks.com
    export DATABRICKS_TOKEN=<a personal access token>

or from a profile in ~/.databrickscfg, which `databricks auth
login` writes after an OAuth sign-in in the browser.

Never put a token in this repository.
