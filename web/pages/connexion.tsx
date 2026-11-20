// Lot 5 — page de connexion / inscription (statique, sans SSR).
// Le cookie de session est HttpOnly : après un succès, le client ne peut pas
// le lire — on renvoie simplement vers « / » qui recharge /api/moi.

import { useEffect, useState } from "react";
import { connecter, inscrire } from "../lib/auth";

type Mode = "login" | "inscription";

// Miroir des règles du serveur (app_store.py) pour des erreurs immédiates.
const LOGIN_RE = /^[a-z0-9][a-z0-9._-]{1,31}$/;

export default function Connexion() {
  const [mode, setMode] = useState<Mode>("login");
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  // Thème persisté côté client (même gabarit que la page catalogue) : jamais
  // de mismatch au rendu initial statique.
  useEffect(() => {
    const saved = window.localStorage.getItem("rtrl-theme");
    if (saved === "dark" || saved === "light") {
      document.documentElement.dataset.theme = saved;
    }
  }, []);

  const changerMode = (m: Mode) => {
    setMode(m);
    setErreur(null);
  };

  const soumettre = async () => {
    if (enCours) return;
    setErreur(null);
    const id = login.trim().toLowerCase();
    if (!LOGIN_RE.test(id)) {
      setErreur(
        "Identifiant invalide : 2 à 32 caractères, lettres minuscules, chiffres, « . _ - », sans espace ni accent."
      );
      return;
    }
    if (password.length < 8) {
      setErreur("Mot de passe trop court (8 caractères minimum).");
      return;
    }
    if (password.length > 128) {
      setErreur("Mot de passe trop long (128 caractères maximum).");
      return;
    }
    if (mode === "inscription" && password !== password2) {
      setErreur("Les deux mots de passe ne sont pas identiques.");
      return;
    }
    setEnCours(true);
    try {
      if (mode === "login") {
        await connecter(id, password);
      } else {
        await inscrire(id, password);
      }
      // Redirection complète : le cookie est posé par le serveur, la page
      // principale recharge l'identité via /api/moi.
      window.location.href = "/";
    } catch (e) {
      setErreur(e instanceof Error ? e.message : "Opération impossible.");
      setEnCours(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-title-row">
          <a className="back-btn" href="/" aria-label="Retour au catalogue">
            ←
          </a>
          <h1 className="app-title">Espace coach</h1>
        </div>
      </header>

      <main className="app-main">
        <div className="connexion-card">
          <div className="connexion-tabs" role="tablist" aria-label="Mode">
            <button
              role="tab"
              aria-selected={mode === "login"}
              className={mode === "login" ? "connexion-tab active" : "connexion-tab"}
              onClick={() => changerMode("login")}
            >
              Connexion
            </button>
            <button
              role="tab"
              aria-selected={mode === "inscription"}
              className={mode === "inscription" ? "connexion-tab active" : "connexion-tab"}
              onClick={() => changerMode("inscription")}
            >
              Créer un compte
            </button>
          </div>

          <form
            className="connexion-form"
            onSubmit={(e) => {
              e.preventDefault();
              void soumettre();
            }}
          >
            <label className="connexion-field">
              <span>Identifiant</span>
              <input
                type="text"
                value={login}
                autoComplete="username"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                pattern="[a-z0-9][a-z0-9._-]{1,31}"
                minLength={2}
                maxLength={32}
                onChange={(e) => setLogin(e.target.value)}
                required
              />
            </label>
            <label className="connexion-field">
              <span>Mot de passe</span>
              <input
                type="password"
                value={password}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                minLength={8}
                maxLength={128}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            {mode === "inscription" && (
              <label className="connexion-field">
                <span>Confirmer le mot de passe</span>
                <input
                  type="password"
                  value={password2}
                  autoComplete="new-password"
                  minLength={8}
                  maxLength={128}
                  onChange={(e) => setPassword2(e.target.value)}
                  required
                />
              </label>
            )}

            {erreur && (
              <p className="connexion-error" role="alert">
                {erreur}
              </p>
            )}

            <button type="submit" className="connexion-submit" disabled={enCours}>
              {enCours ? "…" : mode === "login" ? "Se connecter" : "Créer le compte"}
            </button>
          </form>

          <p className="connexion-note">
            {mode === "login"
              ? "Première visite ? Créez un compte : il suffit d'un identifiant et d'un mot de passe."
              : "Le compte est stocké sur ce serveur, en local, avec votre mot de passe haché."}
          </p>
        </div>
      </main>
    </div>
  );
}
