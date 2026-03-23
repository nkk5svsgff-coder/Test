import React, { useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Animated,
  Image,
  Dimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { Colors, Typography, Spacing, BorderRadius, Shadows } from '../theme';

interface PhotoRevealBannerProps {
  messageCount: number;
  photosRevealed: boolean;
  photoUrl?: string;
  userName?: string;
}

const REVEAL_THRESHOLD = 10;

export const PhotoRevealBanner: React.FC<PhotoRevealBannerProps> = ({
  messageCount,
  photosRevealed,
  photoUrl,
  userName,
}) => {
  const sparkleAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.8)).current;

  useEffect(() => {
    if (photosRevealed) {
      Animated.parallel([
        Animated.spring(scaleAnim, {
          toValue: 1,
          friction: 5,
          useNativeDriver: true,
        }),
        Animated.loop(
          Animated.sequence([
            Animated.timing(sparkleAnim, {
              toValue: 1,
              duration: 1500,
              useNativeDriver: true,
            }),
            Animated.timing(sparkleAnim, {
              toValue: 0,
              duration: 1500,
              useNativeDriver: true,
            }),
          ])
        ),
      ]).start();
    }
  }, [photosRevealed]);

  if (photosRevealed && photoUrl) {
    return (
      <Animated.View
        style={[
          styles.revealedContainer,
          { transform: [{ scale: scaleAnim }] },
        ]}
      >
        <LinearGradient
          colors={Colors.gradientSunset as unknown as [string, string, string]}
          style={styles.revealedGradient}
        >
          <Animated.View style={[styles.sparkle, { opacity: sparkleAnim }]}>
            <Text style={styles.sparkleText}>{'*'}</Text>
          </Animated.View>
          <Image source={{ uri: photoUrl }} style={styles.revealedPhoto} />
          <Text style={styles.revealedText}>
            {userName}'s photo revealed!
          </Text>
          <Text style={styles.revealedSubtext}>
            Your voices connected you first
          </Text>
        </LinearGradient>
      </Animated.View>
    );
  }

  const remaining = REVEAL_THRESHOLD - messageCount;
  const progress = Math.min(messageCount / REVEAL_THRESHOLD, 1);

  return (
    <View style={styles.progressContainer}>
      <LinearGradient
        colors={Colors.gradientSoft as unknown as [string, string, string]}
        style={styles.progressGradient}
      >
        <View style={styles.iconRow}>
          <View style={styles.mysteryPhoto}>
            <Ionicons name="eye-off" size={20} color={Colors.primary} />
          </View>
          <View style={styles.progressInfo}>
            <Text style={styles.progressTitle}>Photo Reveal</Text>
            <Text style={styles.progressSubtext}>
              {remaining > 0
                ? `${remaining} more voice message${remaining === 1 ? '' : 's'} to reveal photos`
                : 'Almost there!'}
            </Text>
          </View>
        </View>

        <View style={styles.progressBarContainer}>
          <View style={styles.progressTrack}>
            <LinearGradient
              colors={Colors.gradientPrimary as unknown as [string, string]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={[styles.progressFill, { width: `${progress * 100}%` }]}
            />
          </View>
          <Text style={styles.progressCount}>
            {messageCount}/{REVEAL_THRESHOLD}
          </Text>
        </View>

        {/* Poppy flower decorations */}
        <View style={styles.flowers}>
          {Array.from({ length: REVEAL_THRESHOLD }).map((_, i) => (
            <View
              key={i}
              style={[
                styles.flowerDot,
                {
                  backgroundColor:
                    i < messageCount ? Colors.primary : Colors.lightGray,
                },
              ]}
            />
          ))}
        </View>
      </LinearGradient>
    </View>
  );
};

const styles = StyleSheet.create({
  progressContainer: {
    marginHorizontal: Spacing.md,
    marginVertical: Spacing.sm,
    borderRadius: BorderRadius.lg,
    ...Shadows.soft,
  },
  progressGradient: {
    borderRadius: BorderRadius.lg,
    padding: Spacing.md,
  },
  iconRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
    marginBottom: Spacing.sm,
  },
  mysteryPhoto: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: Colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: Colors.primary,
    borderStyle: 'dashed',
  },
  progressInfo: {
    flex: 1,
  },
  progressTitle: {
    ...Typography.labelMedium,
    color: Colors.primary,
  },
  progressSubtext: {
    ...Typography.caption,
    color: Colors.gray,
  },
  progressBarContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  progressTrack: {
    flex: 1,
    height: 6,
    backgroundColor: Colors.lightGray,
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 3,
  },
  progressCount: {
    ...Typography.labelSmall,
    color: Colors.primary,
  },
  flowers: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 6,
    marginTop: Spacing.sm,
  },
  flowerDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  revealedContainer: {
    marginHorizontal: Spacing.md,
    marginVertical: Spacing.sm,
    borderRadius: BorderRadius.lg,
    ...Shadows.strong,
  },
  revealedGradient: {
    borderRadius: BorderRadius.lg,
    padding: Spacing.lg,
    alignItems: 'center',
  },
  sparkle: {
    position: 'absolute',
    top: 8,
    right: 16,
  },
  sparkleText: {
    fontSize: 24,
    color: Colors.secondary,
  },
  revealedPhoto: {
    width: 100,
    height: 100,
    borderRadius: 50,
    borderWidth: 3,
    borderColor: Colors.white,
    marginBottom: Spacing.sm,
  },
  revealedText: {
    ...Typography.headlineMedium,
    color: Colors.white,
  },
  revealedSubtext: {
    ...Typography.bodySmall,
    color: 'rgba(255,255,255,0.8)',
  },
});
