import React, { useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Animated,
  Dimensions,
  StatusBar,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Typography, Spacing, BorderRadius, Shadows } from '../../theme';
import { PoppyButton } from '../../components/PoppyButton';

const { width, height } = Dimensions.get('window');

interface WelcomeScreenProps {
  navigation: any;
}

export const WelcomeScreen: React.FC<WelcomeScreenProps> = ({ navigation }) => {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(50)).current;
  const floatAnim = useRef(new Animated.Value(0)).current;
  const petal1 = useRef(new Animated.Value(0)).current;
  const petal2 = useRef(new Animated.Value(0)).current;
  const petal3 = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 1000,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 800,
        useNativeDriver: true,
      }),
    ]).start();

    // Floating animation for the logo
    Animated.loop(
      Animated.sequence([
        Animated.timing(floatAnim, {
          toValue: -10,
          duration: 2000,
          useNativeDriver: true,
        }),
        Animated.timing(floatAnim, {
          toValue: 0,
          duration: 2000,
          useNativeDriver: true,
        }),
      ])
    ).start();

    // Petal animations
    [petal1, petal2, petal3].forEach((petal, i) => {
      Animated.loop(
        Animated.sequence([
          Animated.timing(petal, {
            toValue: 1,
            duration: 3000 + i * 500,
            useNativeDriver: true,
          }),
          Animated.timing(petal, {
            toValue: 0,
            duration: 3000 + i * 500,
            useNativeDriver: true,
          }),
        ])
      ).start();
    });
  }, []);

  return (
    <LinearGradient
      colors={['#FFF0F8', '#FFFFFF', '#FFF5F9'] as [string, string, string]}
      style={styles.container}
    >
      <StatusBar barStyle="dark-content" />

      {/* Decorative floating petals */}
      {[petal1, petal2, petal3].map((petal, i) => (
        <Animated.View
          key={i}
          style={[
            styles.floatingPetal,
            {
              top: [100, 200, 150][i],
              left: [30, width - 60, width / 2 - 10][i],
              backgroundColor: [Colors.primarySoft, Colors.lavender, Colors.rose][i],
              transform: [
                { rotate: `${i * 60}deg` },
                {
                  translateY: petal.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0, -20],
                  }),
                },
              ],
              opacity: petal.interpolate({
                inputRange: [0, 0.5, 1],
                outputRange: [0.3, 0.7, 0.3],
              }),
            },
          ]}
        />
      ))}

      {/* Logo and branding */}
      <Animated.View
        style={[
          styles.logoSection,
          {
            opacity: fadeAnim,
            transform: [{ translateY: floatAnim }],
          },
        ]}
      >
        <View style={styles.logoContainer}>
          <LinearGradient
            colors={Colors.gradientPrimary as unknown as [string, string]}
            style={styles.logoGradient}
          >
            <Ionicons name="mic" size={48} color={Colors.white} />
          </LinearGradient>
          <View style={styles.logoSparkle}>
            <Text style={{ fontSize: 16, color: Colors.secondary }}>{'*'}</Text>
          </View>
        </View>

        <Text style={styles.appName}>Poppy</Text>
        <Text style={styles.tagline}>Where voices bloom into love</Text>
      </Animated.View>

      {/* Features */}
      <Animated.View
        style={[
          styles.features,
          {
            opacity: fadeAnim,
            transform: [{ translateY: slideAnim }],
          },
        ]}
      >
        {[
          { icon: 'mic-outline', text: 'Share your voice, not just a photo' },
          { icon: 'heart-outline', text: 'Fall for personality first' },
          { icon: 'eye-outline', text: 'Photos reveal after 10 messages' },
        ].map((feature, index) => (
          <View key={index} style={styles.featureRow}>
            <View style={styles.featureIcon}>
              <Ionicons
                name={feature.icon as any}
                size={20}
                color={Colors.primary}
              />
            </View>
            <Text style={styles.featureText}>{feature.text}</Text>
          </View>
        ))}
      </Animated.View>

      {/* Action buttons */}
      <Animated.View
        style={[
          styles.actions,
          {
            opacity: fadeAnim,
            transform: [{ translateY: slideAnim }],
          },
        ]}
      >
        <PoppyButton
          title="Create Account"
          onPress={() => navigation.navigate('SignUp')}
          size="large"
        />

        <PoppyButton
          title="I already have an account"
          onPress={() => navigation.navigate('Login')}
          variant="ghost"
          size="medium"
        />
      </Animated.View>

      {/* Bottom flower decoration */}
      <View style={styles.bottomDecor}>
        {[Colors.primary, Colors.primaryLight, Colors.rose, Colors.lavender].map(
          (color, i) => (
            <View
              key={i}
              style={[
                styles.bottomPetal,
                {
                  backgroundColor: color,
                  transform: [{ rotate: `${i * 90}deg` }, { translateY: -8 }],
                  opacity: 0.2,
                },
              ]}
            />
          )
        )}
      </View>
    </LinearGradient>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: Spacing.xl,
    justifyContent: 'center',
  },
  floatingPetal: {
    position: 'absolute',
    width: 24,
    height: 36,
    borderRadius: 18,
  },
  logoSection: {
    alignItems: 'center',
    marginBottom: Spacing.xxl,
  },
  logoContainer: {
    marginBottom: Spacing.md,
  },
  logoGradient: {
    width: 96,
    height: 96,
    borderRadius: 48,
    alignItems: 'center',
    justifyContent: 'center',
    ...Shadows.glow,
  },
  logoSparkle: {
    position: 'absolute',
    top: -4,
    right: -4,
  },
  appName: {
    ...Typography.displayLarge,
    color: Colors.primary,
    marginBottom: Spacing.xs,
  },
  tagline: {
    ...Typography.bodyLarge,
    color: Colors.gray,
    textAlign: 'center',
  },
  features: {
    gap: Spacing.md,
    marginBottom: Spacing.xxl,
  },
  featureRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
    paddingHorizontal: Spacing.md,
  },
  featureIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  featureText: {
    ...Typography.bodyMedium,
    color: Colors.darkGray,
    flex: 1,
  },
  actions: {
    gap: Spacing.md,
    alignItems: 'center',
  },
  bottomDecor: {
    position: 'absolute',
    bottom: 20,
    alignSelf: 'center',
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
  bottomPetal: {
    position: 'absolute',
    width: 16,
    height: 24,
    borderRadius: 12,
  },
});
