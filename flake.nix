{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        postgresqlWithPgvector = pkgs.postgresql_17.withPackages (p: [ p.pgvector p.timescaledb]);

        makePostgresApp = import ./postgres.nix;
        startPostgresDrv = makePostgresApp {
          inherit pkgs;
          postgresqlPackage = postgresqlWithPgvector;
        };
      in
      {

        packages = {
          start-postgres-app = startPostgresDrv;
        };

        apps = {
          start-postgres = flake-utils.lib.mkApp {
            drv = startPostgresDrv;
          };
        };

        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            postgresqlWithPgvector
            glibcLocales
          ];

          shellHook = ''
            echo "--- Entering Nix develop Shell ---"          
            echo "Setting ENV VARS (Secrets -> .env + direnv)..."
            export PORT=3000 JOBS_PORT=3000
            echo "-----------------------------------"
            echo "Nix develop Shell is ready!"
            echo "-----------------------------------"
            echo "PostgreSQL tools (e.g., psql) available."
            echo "Run 'nix run .#start-postgres' in a separate terminal to start DB."
            echo "-----------------------------------"
          '';
        };
      }
    );
}