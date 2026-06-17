module.exports = {
  webpack: {
    configure: (webpackConfig) => {
      // Ignore source map warnings from specific packages
      webpackConfig.ignoreWarnings = [
        function ignoreSourcemapsloaderWarnings(warning) {
          return (
            warning.module &&
            warning.module.resource.includes('@mediapipe') &&
            warning.details &&
            warning.details.includes('source map')
          );
        },
      ];
      return webpackConfig;
    },
  },
};
