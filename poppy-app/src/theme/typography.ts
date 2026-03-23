// Typography inspired by Poppi's Recoleta + clean sans-serif approach
import { Platform } from 'react-native';

const fontFamily = Platform.select({
  ios: 'System',
  android: 'sans-serif',
  web: '"Georgia", "Times New Roman", serif',
});

const fontFamilySans = Platform.select({
  ios: 'System',
  android: 'sans-serif',
  web: '"Avenir", "Helvetica Neue", sans-serif',
});

export const Typography = {
  // Display - large headlines
  displayLarge: {
    fontFamily,
    fontSize: 40,
    fontWeight: '700' as const,
    lineHeight: 48,
    letterSpacing: -0.5,
  },
  displayMedium: {
    fontFamily,
    fontSize: 32,
    fontWeight: '700' as const,
    lineHeight: 40,
    letterSpacing: -0.3,
  },
  displaySmall: {
    fontFamily,
    fontSize: 28,
    fontWeight: '600' as const,
    lineHeight: 36,
  },

  // Headlines
  headlineLarge: {
    fontFamily: fontFamilySans,
    fontSize: 24,
    fontWeight: '700' as const,
    lineHeight: 32,
  },
  headlineMedium: {
    fontFamily: fontFamilySans,
    fontSize: 20,
    fontWeight: '600' as const,
    lineHeight: 28,
  },
  headlineSmall: {
    fontFamily: fontFamilySans,
    fontSize: 18,
    fontWeight: '600' as const,
    lineHeight: 24,
  },

  // Body
  bodyLarge: {
    fontFamily: fontFamilySans,
    fontSize: 16,
    fontWeight: '400' as const,
    lineHeight: 24,
  },
  bodyMedium: {
    fontFamily: fontFamilySans,
    fontSize: 14,
    fontWeight: '400' as const,
    lineHeight: 20,
  },
  bodySmall: {
    fontFamily: fontFamilySans,
    fontSize: 12,
    fontWeight: '400' as const,
    lineHeight: 16,
  },

  // Labels
  labelLarge: {
    fontFamily: fontFamilySans,
    fontSize: 16,
    fontWeight: '600' as const,
    lineHeight: 22,
  },
  labelMedium: {
    fontFamily: fontFamilySans,
    fontSize: 14,
    fontWeight: '600' as const,
    lineHeight: 18,
  },
  labelSmall: {
    fontFamily: fontFamilySans,
    fontSize: 11,
    fontWeight: '500' as const,
    lineHeight: 16,
    letterSpacing: 0.5,
  },

  // Special
  button: {
    fontFamily: fontFamilySans,
    fontSize: 16,
    fontWeight: '700' as const,
    lineHeight: 22,
    letterSpacing: 0.8,
  },
  caption: {
    fontFamily: fontFamilySans,
    fontSize: 12,
    fontWeight: '400' as const,
    lineHeight: 16,
    letterSpacing: 0.3,
  },
};
