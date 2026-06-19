(() => {
  const host = window.location.hostname || "127.0.0.1";
  window.URI_RUN_NOVNC_CONFIG = window.URI_RUN_NOVNC_CONFIG || {
    pcs: {
      desktop: { novncPort: "7901", apiPort: "18765" },
      laptop: { novncPort: "7902", apiPort: "18766" },
    },
  };
  window.URI_RUN_NOVNC_HOST = window.URI_RUN_NOVNC_HOST || host;
})();
