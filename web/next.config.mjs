/** @type {import('next').NextConfig} */
const nextConfig = {
  // Export statique : web/out/, servi par webapp.py (aucun runtime Node en prod).
  output: "export",
  reactStrictMode: true,
};

export default nextConfig;
