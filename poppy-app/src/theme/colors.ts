// Poppy Dating App - Color palette inspired by drinkpoppi.com
// Feminine, vibrant, playful aesthetic

export const Colors = {
  // Primary palette
  primary: '#EC008C',        // Poppi pink - main brand color
  primaryLight: '#FF4DB8',   // Lighter pink for highlights
  primarySoft: '#FFF0F8',    // Very soft pink for backgrounds
  primaryDark: '#C70076',    // Darker pink for pressed states

  // Secondary palette
  secondary: '#FFF200',      // Poppi yellow - accents & highlights
  secondaryLight: '#FFF766', // Light yellow
  secondarySoft: '#FFFDE6',  // Soft yellow background

  // Tertiary palette
  tertiary: '#00AEEF',       // Poppi blue - complementary accent
  tertiaryLight: '#66D4FF',  // Light blue
  tertiarySoft: '#E6F8FF',   // Soft blue background

  // Warm accents
  coral: '#FF6B6B',          // Warm coral for hearts/love
  peach: '#FFAB91',          // Soft peach
  lavender: '#E8D5F5',      // Soft lavender
  mint: '#B2F5EA',           // Fresh mint accent
  rose: '#FFB6C1',           // Light rose

  // Neutrals
  white: '#FFFFFF',
  offWhite: '#FFF8FC',       // Slightly warm white
  cream: '#FFF5F9',          // Cream with pink tint
  lightGray: '#F5F0F3',     // Light gray with warmth
  gray: '#B8A8B0',          // Warm gray
  darkGray: '#6B5C63',      // Dark warm gray
  charcoal: '#3F3F3F',      // Near black
  black: '#1A1A1A',         // Soft black

  // Functional
  success: '#4CAF50',
  warning: '#FFC107',
  error: '#FF5252',
  info: '#00AEEF',

  // Gradients (used as arrays for LinearGradient)
  gradientPrimary: ['#EC008C', '#FF4DB8'],
  gradientSunset: ['#EC008C', '#FF6B6B', '#FFAB91'],
  gradientDream: ['#EC008C', '#E8D5F5', '#00AEEF'],
  gradientSoft: ['#FFF0F8', '#FFF5F9', '#FFFFFF'],
  gradientCard: ['#FFFFFF', '#FFF8FC'],
  gradientVoice: ['#EC008C', '#FF4DB8', '#FF6B6B'],
} as const;
