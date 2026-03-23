import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Dimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { Colors, Typography, Spacing, BorderRadius, Shadows } from '../theme';
import { VoiceWaveform } from './VoiceWaveform';
import { User } from '../types';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CARD_WIDTH = SCREEN_WIDTH - 40;

interface VoiceCardProps {
  user: User;
  onLike: () => void;
  onPass: () => void;
  onSuperLike: () => void;
}

export const VoiceCard: React.FC<VoiceCardProps> = ({
  user,
  onLike,
  onPass,
  onSuperLike,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [playProgress, setPlayProgress] = useState(0);
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.95)).current;
  const progressRef = useRef<ReturnType<typeof setInterval>>(undefined);

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 400,
        useNativeDriver: true,
      }),
      Animated.spring(scaleAnim, {
        toValue: 1,
        friction: 8,
        useNativeDriver: true,
      }),
    ]).start();
  }, []);

  const togglePlay = () => {
    if (isPlaying) {
      setIsPlaying(false);
      if (progressRef.current) clearInterval(progressRef.current);
    } else {
      setIsPlaying(true);
      setPlayProgress(0);
      progressRef.current = setInterval(() => {
        setPlayProgress(prev => {
          if (prev >= 100) {
            setIsPlaying(false);
            if (progressRef.current) clearInterval(progressRef.current);
            return 0;
          }
          return prev + (100 / (user.voiceIntroDuration * 10));
        });
      }, 100);
    }
  };

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Generate flower petal decorations
  const renderFlowerDecor = () => (
    <View style={styles.decorContainer}>
      {['#EC008C', '#FF4DB8', '#FFB6C1', '#E8D5F5'].map((color, i) => (
        <View
          key={i}
          style={[
            styles.petal,
            {
              backgroundColor: color,
              top: [15, 60, 20, 70][i],
              right: [15, 30, 50, 10][i],
              transform: [{ rotate: `${i * 45}deg` }],
              opacity: 0.15,
            },
          ]}
        />
      ))}
    </View>
  );

  return (
    <Animated.View
      style={[
        styles.card,
        {
          opacity: fadeAnim,
          transform: [{ scale: scaleAnim }],
        },
      ]}
    >
      <LinearGradient
        colors={['#FFFFFF', '#FFF8FC', '#FFF0F8'] as [string, string, string]}
        style={styles.cardGradient}
      >
        {renderFlowerDecor()}

        {/* Header with poppy flower icon */}
        <View style={styles.header}>
          <View style={styles.flowerIcon}>
            <Text style={styles.flowerEmoji}>{'~'}</Text>
          </View>
          <View>
            <Text style={styles.name}>{user.name}, {user.age}</Text>
            <View style={styles.locationRow}>
              <Ionicons name="location-outline" size={14} color={Colors.gray} />
              <Text style={styles.location}>{user.location}</Text>
            </View>
          </View>
          {user.verified && (
            <View style={styles.verifiedBadge}>
              <Ionicons name="checkmark-circle" size={20} color={Colors.primary} />
            </View>
          )}
        </View>

        {/* Voice message area - the star of the show */}
        <View style={styles.voiceArea}>
          <TouchableOpacity
            onPress={togglePlay}
            style={styles.playButton}
            activeOpacity={0.8}
          >
            <LinearGradient
              colors={Colors.gradientVoice as unknown as [string, string, string]}
              style={styles.playGradient}
            >
              <Ionicons
                name={isPlaying ? 'pause' : 'play'}
                size={32}
                color={Colors.white}
              />
            </LinearGradient>
          </TouchableOpacity>

          <View style={styles.waveformContainer}>
            <VoiceWaveform
              isPlaying={isPlaying}
              color={Colors.primary}
              height={48}
              barCount={25}
            />
            <View style={styles.progressBar}>
              <View
                style={[styles.progressFill, { width: `${playProgress}%` }]}
              />
            </View>
          </View>

          <Text style={styles.duration}>
            {formatDuration(user.voiceIntroDuration)}
          </Text>
        </View>

        {/* Bio */}
        <Text style={styles.bio}>"{user.bio}"</Text>

        {/* Interests */}
        <View style={styles.interests}>
          {user.interests.map((interest, index) => (
            <View key={index} style={styles.interestTag}>
              <Text style={styles.interestText}>{interest}</Text>
            </View>
          ))}
        </View>

        {/* Photo hidden notice */}
        <View style={styles.photoNotice}>
          <Ionicons name="eye-off-outline" size={16} color={Colors.gray} />
          <Text style={styles.photoNoticeText}>
            Photo revealed after 10 voice messages
          </Text>
        </View>

        {/* Action buttons */}
        <View style={styles.actions}>
          <TouchableOpacity
            onPress={onPass}
            style={[styles.actionBtn, styles.passBtn]}
            activeOpacity={0.7}
          >
            <Ionicons name="close" size={28} color={Colors.gray} />
          </TouchableOpacity>

          <TouchableOpacity
            onPress={onSuperLike}
            style={[styles.actionBtn, styles.superLikeBtn]}
            activeOpacity={0.7}
          >
            <Ionicons name="star" size={24} color={Colors.secondary} />
          </TouchableOpacity>

          <TouchableOpacity
            onPress={onLike}
            style={[styles.actionBtn, styles.likeBtn]}
            activeOpacity={0.7}
          >
            <LinearGradient
              colors={Colors.gradientPrimary as unknown as [string, string]}
              style={styles.likeBtnGradient}
            >
              <Ionicons name="heart" size={28} color={Colors.white} />
            </LinearGradient>
          </TouchableOpacity>
        </View>
      </LinearGradient>
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  card: {
    width: CARD_WIDTH,
    borderRadius: BorderRadius.xl,
    ...Shadows.strong,
    marginHorizontal: 20,
  },
  cardGradient: {
    borderRadius: BorderRadius.xl,
    padding: Spacing.lg,
    overflow: 'hidden',
  },
  decorContainer: {
    position: 'absolute',
    top: 0,
    right: 0,
    width: 100,
    height: 100,
  },
  petal: {
    position: 'absolute',
    width: 20,
    height: 30,
    borderRadius: 15,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
    marginBottom: Spacing.lg,
  },
  flowerIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: Colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  flowerEmoji: {
    fontSize: 24,
    color: Colors.primary,
    fontWeight: '700',
  },
  name: {
    ...Typography.headlineLarge,
    color: Colors.black,
  },
  locationRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  location: {
    ...Typography.bodySmall,
    color: Colors.gray,
  },
  verifiedBadge: {
    marginLeft: 'auto',
  },
  voiceArea: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
    backgroundColor: Colors.white,
    borderRadius: BorderRadius.lg,
    padding: Spacing.md,
    marginBottom: Spacing.lg,
    ...Shadows.soft,
  },
  playButton: {
    ...Shadows.glow,
  },
  playGradient: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  waveformContainer: {
    flex: 1,
  },
  progressBar: {
    height: 3,
    backgroundColor: Colors.lightGray,
    borderRadius: 2,
    marginTop: Spacing.sm,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: Colors.primary,
    borderRadius: 2,
  },
  duration: {
    ...Typography.labelSmall,
    color: Colors.gray,
  },
  bio: {
    ...Typography.bodyLarge,
    color: Colors.darkGray,
    fontStyle: 'italic',
    textAlign: 'center',
    marginBottom: Spacing.lg,
    paddingHorizontal: Spacing.md,
  },
  interests: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
    justifyContent: 'center',
    marginBottom: Spacing.lg,
  },
  interestTag: {
    backgroundColor: Colors.primarySoft,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.round,
    borderWidth: 1,
    borderColor: Colors.rose,
  },
  interestText: {
    ...Typography.labelSmall,
    color: Colors.primary,
  },
  photoNotice: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.xs,
    marginBottom: Spacing.lg,
    opacity: 0.6,
  },
  photoNoticeText: {
    ...Typography.caption,
    color: Colors.gray,
  },
  actions: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: Spacing.lg,
  },
  actionBtn: {
    ...Shadows.soft,
  },
  passBtn: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: Colors.white,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: Colors.lightGray,
  },
  superLikeBtn: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: Colors.white,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: Colors.secondaryLight,
  },
  likeBtn: {
    ...Shadows.glow,
  },
  likeBtnGradient: {
    width: 64,
    height: 64,
    borderRadius: 32,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
