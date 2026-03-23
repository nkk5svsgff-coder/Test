import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Animated,
  Dimensions,
  StatusBar,
  PanResponder,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Typography, Spacing, Shadows } from '../../theme';
import { VoiceCard } from '../../components/VoiceCard';
import { useApp } from '../../context/AppContext';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const SWIPE_THRESHOLD = SCREEN_WIDTH * 0.25;

export const DiscoverScreen: React.FC = () => {
  const { profiles, currentProfileIndex, swipeLike, swipePass, swipeSuperLike } =
    useApp();
  const [matchAnimation, setMatchAnimation] = useState(false);
  const position = useRef(new Animated.ValueXY()).current;
  const rotateAnim = useRef(new Animated.Value(0)).current;
  const matchScale = useRef(new Animated.Value(0)).current;

  const currentProfile = profiles[currentProfileIndex];

  const panResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_, gestureState) =>
        Math.abs(gestureState.dx) > 10,
      onPanResponderMove: (_, gestureState) => {
        position.setValue({ x: gestureState.dx, y: gestureState.dy * 0.3 });
      },
      onPanResponderRelease: (_, gestureState) => {
        if (gestureState.dx > SWIPE_THRESHOLD) {
          // Swiped right - LIKE
          Animated.timing(position, {
            toValue: { x: SCREEN_WIDTH + 100, y: gestureState.dy },
            duration: 300,
            useNativeDriver: true,
          }).start(() => {
            handleLike();
            position.setValue({ x: 0, y: 0 });
          });
        } else if (gestureState.dx < -SWIPE_THRESHOLD) {
          // Swiped left - PASS
          Animated.timing(position, {
            toValue: { x: -SCREEN_WIDTH - 100, y: gestureState.dy },
            duration: 300,
            useNativeDriver: true,
          }).start(() => {
            swipePass();
            position.setValue({ x: 0, y: 0 });
          });
        } else {
          // Snap back
          Animated.spring(position, {
            toValue: { x: 0, y: 0 },
            friction: 5,
            useNativeDriver: true,
          }).start();
        }
      },
    })
  ).current;

  const handleLike = () => {
    // Show match animation randomly
    if (Math.random() < 0.3) {
      setMatchAnimation(true);
      Animated.sequence([
        Animated.spring(matchScale, {
          toValue: 1,
          friction: 5,
          useNativeDriver: true,
        }),
        Animated.delay(2000),
        Animated.timing(matchScale, {
          toValue: 0,
          duration: 300,
          useNativeDriver: true,
        }),
      ]).start(() => setMatchAnimation(false));
    }
    swipeLike();
  };

  const rotate = position.x.interpolate({
    inputRange: [-SCREEN_WIDTH / 2, 0, SCREEN_WIDTH / 2],
    outputRange: ['-8deg', '0deg', '8deg'],
    extrapolate: 'clamp',
  });

  const likeOpacity = position.x.interpolate({
    inputRange: [0, SCREEN_WIDTH / 4],
    outputRange: [0, 1],
    extrapolate: 'clamp',
  });

  const passOpacity = position.x.interpolate({
    inputRange: [-SCREEN_WIDTH / 4, 0],
    outputRange: [1, 0],
    extrapolate: 'clamp',
  });

  if (!currentProfile) {
    return (
      <LinearGradient
        colors={['#FFF0F8', '#FFFFFF', '#FFF5F9'] as [string, string, string]}
        style={styles.emptyContainer}
      >
        <StatusBar barStyle="dark-content" />
        <View style={styles.emptyContent}>
          <View style={styles.emptyIcon}>
            <Ionicons name="flower-outline" size={64} color={Colors.primary} />
          </View>
          <Text style={styles.emptyTitle}>No more voices</Text>
          <Text style={styles.emptySubtitle}>
            Come back later for new voice intros.{'\n'}
            Your perfect match might be recording right now!
          </Text>
        </View>
      </LinearGradient>
    );
  }

  return (
    <LinearGradient
      colors={['#FFF0F8', '#FFFFFF', '#FFF5F9'] as [string, string, string]}
      style={styles.container}
    >
      <StatusBar barStyle="dark-content" />

      {/* Header */}
      <View style={styles.header}>
        <View style={styles.logoRow}>
          <LinearGradient
            colors={Colors.gradientPrimary as unknown as [string, string]}
            style={styles.miniLogo}
          >
            <Ionicons name="mic" size={18} color={Colors.white} />
          </LinearGradient>
          <Text style={styles.headerTitle}>Poppy</Text>
        </View>
        <View style={styles.headerRight}>
          <View style={styles.notifBadge}>
            <Ionicons name="notifications-outline" size={22} color={Colors.primary} />
            <View style={styles.notifDot} />
          </View>
        </View>
      </View>

      {/* Swipeable card area */}
      <View style={styles.cardArea}>
        <Animated.View
          style={[
            styles.cardWrapper,
            {
              transform: [
                { translateX: position.x },
                { translateY: position.y },
                { rotate },
              ],
            },
          ]}
          {...panResponder.panHandlers}
        >
          {/* Like/Pass overlays */}
          <Animated.View style={[styles.likeOverlay, { opacity: likeOpacity }]}>
            <Text style={styles.overlayText}>LIKE</Text>
            <Ionicons name="heart" size={32} color={Colors.primary} />
          </Animated.View>

          <Animated.View style={[styles.passOverlay, { opacity: passOpacity }]}>
            <Text style={styles.overlayTextPass}>PASS</Text>
            <Ionicons name="close" size={32} color={Colors.gray} />
          </Animated.View>

          <VoiceCard
            user={currentProfile}
            onLike={handleLike}
            onPass={swipePass}
            onSuperLike={swipeSuperLike}
          />
        </Animated.View>
      </View>

      {/* Swipe hints */}
      <View style={styles.hints}>
        <View style={styles.hintItem}>
          <Ionicons name="arrow-back" size={16} color={Colors.gray} />
          <Text style={styles.hintText}>Pass</Text>
        </View>
        <View style={styles.hintItem}>
          <Ionicons name="arrow-forward" size={16} color={Colors.primary} />
          <Text style={[styles.hintText, { color: Colors.primary }]}>Like</Text>
        </View>
      </View>

      {/* Match animation overlay */}
      {matchAnimation && (
        <Animated.View
          style={[
            styles.matchOverlay,
            { transform: [{ scale: matchScale }] },
          ]}
        >
          <LinearGradient
            colors={['rgba(236,0,140,0.95)', 'rgba(255,77,184,0.95)'] as [string, string]}
            style={styles.matchContent}
          >
            <Text style={styles.matchEmoji}>{'*'}</Text>
            <Text style={styles.matchTitle}>It's a Match!</Text>
            <Text style={styles.matchSubtitle}>
              Start a voice conversation with {currentProfile?.name}
            </Text>
            <Ionicons name="mic" size={48} color={Colors.white} />
          </LinearGradient>
        </Animated.View>
      )}
    </LinearGradient>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.xxl + 10,
    paddingBottom: Spacing.sm,
  },
  logoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  miniLogo: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    ...Typography.headlineLarge,
    color: Colors.primary,
  },
  headerRight: {
    flexDirection: 'row',
    gap: Spacing.md,
  },
  notifBadge: {
    position: 'relative',
  },
  notifDot: {
    position: 'absolute',
    top: 0,
    right: 0,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: Colors.primary,
  },
  cardArea: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  cardWrapper: {
    width: '100%',
    alignItems: 'center',
  },
  likeOverlay: {
    position: 'absolute',
    top: 30,
    left: 40,
    zIndex: 10,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    borderWidth: 3,
    borderColor: Colors.primary,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: 'rgba(255,255,255,0.9)',
    transform: [{ rotate: '-15deg' }],
  },
  passOverlay: {
    position: 'absolute',
    top: 30,
    right: 40,
    zIndex: 10,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    borderWidth: 3,
    borderColor: Colors.gray,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: 'rgba(255,255,255,0.9)',
    transform: [{ rotate: '15deg' }],
  },
  overlayText: {
    ...Typography.headlineLarge,
    color: Colors.primary,
  },
  overlayTextPass: {
    ...Typography.headlineLarge,
    color: Colors.gray,
  },
  hints: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: Spacing.xxl,
    paddingBottom: Spacing.lg,
  },
  hintItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  hintText: {
    ...Typography.caption,
    color: Colors.gray,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyContent: {
    alignItems: 'center',
    padding: Spacing.xxl,
  },
  emptyIcon: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: Colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.lg,
    ...Shadows.glow,
  },
  emptyTitle: {
    ...Typography.displaySmall,
    color: Colors.primary,
    marginBottom: Spacing.sm,
  },
  emptySubtitle: {
    ...Typography.bodyMedium,
    color: Colors.gray,
    textAlign: 'center',
  },
  matchOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 100,
  },
  matchContent: {
    width: '80%',
    borderRadius: 32,
    padding: Spacing.xxl,
    alignItems: 'center',
    gap: Spacing.md,
    ...Shadows.strong,
  },
  matchEmoji: {
    fontSize: 48,
    color: Colors.secondary,
  },
  matchTitle: {
    ...Typography.displayMedium,
    color: Colors.white,
  },
  matchSubtitle: {
    ...Typography.bodyLarge,
    color: 'rgba(255,255,255,0.8)',
    textAlign: 'center',
  },
});
