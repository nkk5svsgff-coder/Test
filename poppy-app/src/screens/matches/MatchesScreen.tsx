import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Image,
  StatusBar,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Typography, Spacing, BorderRadius, Shadows } from '../../theme';
import { VoiceWaveform } from '../../components/VoiceWaveform';
import { useApp } from '../../context/AppContext';
import { Match } from '../../types';

interface MatchesScreenProps {
  navigation: any;
}

export const MatchesScreen: React.FC<MatchesScreenProps> = ({ navigation }) => {
  const { matches, getMatchUser, currentUser } = useApp();

  const formatTime = (date: Date): string => {
    const d = new Date(date);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  const renderMatchItem = ({ item }: { item: Match }) => {
    const user = getMatchUser(item);
    if (!user) return null;

    const progressPercent = Math.min(item.messageCount / 10, 1) * 100;

    return (
      <TouchableOpacity
        style={styles.matchItem}
        onPress={() =>
          navigation.navigate('Chat', {
            matchId: item.id,
            userName: user.name,
            photoUrl: user.photoUrl,
            photosRevealed: item.photosRevealed,
            messageCount: item.messageCount,
          })
        }
        activeOpacity={0.7}
      >
        {/* Avatar area */}
        <View style={styles.avatarContainer}>
          {item.photosRevealed ? (
            <Image source={{ uri: user.photoUrl }} style={styles.avatar} />
          ) : (
            <LinearGradient
              colors={Colors.gradientDream as unknown as [string, string, string]}
              style={styles.avatarMystery}
            >
              <Ionicons name="mic" size={24} color={Colors.white} />
            </LinearGradient>
          )}
          {/* Progress ring */}
          {!item.photosRevealed && (
            <View style={styles.progressRing}>
              <Text style={styles.progressText}>
                {item.messageCount}/10
              </Text>
            </View>
          )}
          {item.unreadCount > 0 && (
            <View style={styles.unreadBadge}>
              <Text style={styles.unreadText}>{item.unreadCount}</Text>
            </View>
          )}
        </View>

        {/* Info */}
        <View style={styles.matchInfo}>
          <View style={styles.matchHeader}>
            <Text style={styles.matchName}>{user.name}, {user.age}</Text>
            {item.lastMessage && (
              <Text style={styles.matchTime}>
                {formatTime(item.lastMessage.timestamp)}
              </Text>
            )}
          </View>

          {/* Last voice message preview */}
          {item.lastMessage ? (
            <View style={styles.voicePreview}>
              <Ionicons
                name="mic"
                size={14}
                color={item.unreadCount > 0 ? Colors.primary : Colors.gray}
              />
              <VoiceWaveform
                waveform={item.lastMessage.waveform}
                color={item.unreadCount > 0 ? Colors.primary : Colors.gray}
                height={18}
                barCount={12}
              />
              <Text
                style={[
                  styles.voiceDuration,
                  item.unreadCount > 0 && { color: Colors.primary },
                ]}
              >
                {Math.floor(item.lastMessage.duration / 60)}:
                {(item.lastMessage.duration % 60).toString().padStart(2, '0')}
              </Text>
            </View>
          ) : (
            <Text style={styles.newMatchText}>
              New match! Send a voice message
            </Text>
          )}

          {/* Photo reveal progress bar */}
          {!item.photosRevealed && (
            <View style={styles.revealProgress}>
              <View style={styles.revealTrack}>
                <LinearGradient
                  colors={Colors.gradientPrimary as unknown as [string, string]}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 0 }}
                  style={[styles.revealFill, { width: `${progressPercent}%` }]}
                />
              </View>
              <Ionicons name="eye-outline" size={12} color={Colors.gray} />
            </View>
          )}
        </View>
      </TouchableOpacity>
    );
  };

  const newMatches = matches.filter(m => m.messageCount === 0);
  const conversations = matches.filter(m => m.messageCount > 0);

  return (
    <LinearGradient
      colors={['#FFF0F8', '#FFFFFF'] as [string, string]}
      style={styles.container}
    >
      <StatusBar barStyle="dark-content" />

      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Messages</Text>
        <View style={styles.headerBadge}>
          <Ionicons name="chatbubble-ellipses" size={20} color={Colors.primary} />
          <Text style={styles.headerCount}>{matches.length}</Text>
        </View>
      </View>

      <FlatList
        data={[...conversations, ...newMatches]}
        renderItem={renderMatchItem}
        keyExtractor={item => item.id}
        contentContainerStyle={styles.list}
        showsVerticalScrollIndicator={false}
        ListHeaderComponent={
          newMatches.length > 0 ? (
            <View style={styles.sectionHeader}>
              <View style={styles.sectionIcon}>
                <Ionicons name="sparkles" size={14} color={Colors.primary} />
              </View>
              <Text style={styles.sectionTitle}>
                {newMatches.length} new {newMatches.length === 1 ? 'match' : 'matches'}
              </Text>
            </View>
          ) : null
        }
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <View style={styles.emptyIcon}>
              <Ionicons name="chatbubbles-outline" size={48} color={Colors.primary} />
            </View>
            <Text style={styles.emptyTitle}>No matches yet</Text>
            <Text style={styles.emptySubtitle}>
              Keep swiping to find your voice match!
            </Text>
          </View>
        }
      />
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
    paddingBottom: Spacing.md,
  },
  headerTitle: {
    ...Typography.displaySmall,
    color: Colors.primary,
  },
  headerBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: Colors.primarySoft,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.round,
  },
  headerCount: {
    ...Typography.labelMedium,
    color: Colors.primary,
  },
  list: {
    paddingHorizontal: Spacing.md,
    paddingBottom: 100,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.sm,
  },
  sectionIcon: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: Colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sectionTitle: {
    ...Typography.labelMedium,
    color: Colors.primary,
  },
  matchItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: Spacing.md,
    backgroundColor: Colors.white,
    borderRadius: BorderRadius.lg,
    marginBottom: Spacing.sm,
    gap: Spacing.md,
    ...Shadows.soft,
  },
  avatarContainer: {
    position: 'relative',
  },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    borderWidth: 2,
    borderColor: Colors.primary,
  },
  avatarMystery: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  progressRing: {
    position: 'absolute',
    bottom: -4,
    right: -4,
    backgroundColor: Colors.white,
    borderRadius: 10,
    paddingHorizontal: 4,
    paddingVertical: 1,
    ...Shadows.soft,
  },
  progressText: {
    ...Typography.caption,
    color: Colors.primary,
    fontSize: 9,
    fontWeight: '700',
  },
  unreadBadge: {
    position: 'absolute',
    top: -4,
    right: -4,
    backgroundColor: Colors.primary,
    borderRadius: 10,
    minWidth: 20,
    height: 20,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 4,
  },
  unreadText: {
    ...Typography.caption,
    color: Colors.white,
    fontSize: 10,
    fontWeight: '700',
  },
  matchInfo: {
    flex: 1,
  },
  matchHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  matchName: {
    ...Typography.headlineSmall,
    color: Colors.black,
  },
  matchTime: {
    ...Typography.caption,
    color: Colors.gray,
  },
  voicePreview: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
  },
  voiceDuration: {
    ...Typography.caption,
    color: Colors.gray,
  },
  newMatchText: {
    ...Typography.bodySmall,
    color: Colors.primary,
    fontStyle: 'italic',
  },
  revealProgress: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 6,
  },
  revealTrack: {
    flex: 1,
    height: 3,
    backgroundColor: Colors.lightGray,
    borderRadius: 2,
    overflow: 'hidden',
  },
  revealFill: {
    height: '100%',
    borderRadius: 2,
  },
  emptyState: {
    alignItems: 'center',
    paddingTop: Spacing.xxxl,
  },
  emptyIcon: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: Colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.lg,
  },
  emptyTitle: {
    ...Typography.headlineMedium,
    color: Colors.primary,
  },
  emptySubtitle: {
    ...Typography.bodyMedium,
    color: Colors.gray,
    marginTop: Spacing.xs,
  },
});
