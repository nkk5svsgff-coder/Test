import React from 'react';
import {
  TouchableOpacity,
  Text,
  StyleSheet,
  ViewStyle,
  TextStyle,
  ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Colors, Typography, BorderRadius, Shadows, Spacing } from '../theme';

interface PoppyButtonProps {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
  size?: 'small' | 'medium' | 'large';
  disabled?: boolean;
  loading?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
  icon?: React.ReactNode;
}

export const PoppyButton: React.FC<PoppyButtonProps> = ({
  title,
  onPress,
  variant = 'primary',
  size = 'medium',
  disabled = false,
  loading = false,
  style,
  textStyle,
  icon,
}) => {
  const sizeStyles = {
    small: { paddingVertical: 8, paddingHorizontal: 20 },
    medium: { paddingVertical: 14, paddingHorizontal: 32 },
    large: { paddingVertical: 18, paddingHorizontal: 48 },
  };

  const textSizes = {
    small: { fontSize: 13 },
    medium: { fontSize: 16 },
    large: { fontSize: 18 },
  };

  if (variant === 'primary') {
    return (
      <TouchableOpacity
        onPress={onPress}
        disabled={disabled || loading}
        activeOpacity={0.8}
        style={[styles.wrapper, style]}
      >
        <LinearGradient
          colors={disabled ? ['#ccc', '#aaa'] : Colors.gradientPrimary as unknown as [string, string]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0 }}
          style={[styles.gradient, sizeStyles[size], Shadows.medium]}
        >
          {loading ? (
            <ActivityIndicator color={Colors.white} />
          ) : (
            <>
              {icon}
              <Text style={[styles.primaryText, textSizes[size], textStyle]}>
                {title}
              </Text>
            </>
          )}
        </LinearGradient>
      </TouchableOpacity>
    );
  }

  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled || loading}
      activeOpacity={0.7}
      style={[
        styles.base,
        sizeStyles[size],
        variant === 'secondary' && styles.secondary,
        variant === 'outline' && styles.outline,
        variant === 'ghost' && styles.ghost,
        disabled && styles.disabled,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator
          color={variant === 'outline' ? Colors.primary : Colors.white}
        />
      ) : (
        <>
          {icon}
          <Text
            style={[
              styles.text,
              textSizes[size],
              variant === 'secondary' && styles.secondaryText,
              variant === 'outline' && styles.outlineText,
              variant === 'ghost' && styles.ghostText,
              textStyle,
            ]}
          >
            {title}
          </Text>
        </>
      )}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  wrapper: {
    alignSelf: 'stretch',
  },
  gradient: {
    borderRadius: BorderRadius.round,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
  },
  base: {
    borderRadius: BorderRadius.round,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
  },
  secondary: {
    backgroundColor: Colors.primarySoft,
  },
  outline: {
    backgroundColor: 'transparent',
    borderWidth: 2,
    borderColor: Colors.primary,
  },
  ghost: {
    backgroundColor: 'transparent',
  },
  disabled: {
    opacity: 0.5,
  },
  primaryText: {
    ...Typography.button,
    color: Colors.white,
  },
  text: {
    ...Typography.button,
    color: Colors.white,
  },
  secondaryText: {
    color: Colors.primary,
  },
  outlineText: {
    color: Colors.primary,
  },
  ghostText: {
    color: Colors.primary,
  },
});
