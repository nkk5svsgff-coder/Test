export const Spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
  xxxl: 64,
} as const;

export const BorderRadius = {
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  round: 9999,
} as const;

export const Shadows = {
  soft: {
    shadowColor: '#EC008C',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 2,
  },
  medium: {
    shadowColor: '#EC008C',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.12,
    shadowRadius: 16,
    elevation: 4,
  },
  strong: {
    shadowColor: '#EC008C',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.18,
    shadowRadius: 24,
    elevation: 8,
  },
  glow: {
    shadowColor: '#EC008C',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.3,
    shadowRadius: 20,
    elevation: 6,
  },
} as const;
