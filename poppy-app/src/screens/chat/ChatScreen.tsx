import React, { useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Image,
  StatusBar,
  Animated,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Typography, Spacing, BorderRadius, Shadows } from '../../theme';
import { VoiceMessageBubble } from '../../components/VoiceMessageBubble';
import { VoiceRecordButton } from '../../components/VoiceRecordButton';
import { PhotoRevealBanner } from '../../components/PhotoRevealBanner';
import { useApp } from '../../context/AppContext';

interface ChatScreenProps {
  navigation: any;
  route: any;
}

export const ChatScreen: React.FC<ChatScreenProps> = ({ navigation, route }) => {
  const { matchId, userName, photoUrl, photosRevealed, messageCount } = route.params;
  const { getMessages, sendVoiceMessage, currentUser, matches } = useApp();
  const messages = getMessages(matchId);
  const flatListRef = useRef<FlatList>(null);
  const slideUpAnim = useRef(new Animated.Value(100)).current;

  // Get latest match state
  const match = matches.find(m => m.id === matchId);
  const currentMessageCount = match?.messageCount || messageCount;
  const currentPhotosRevealed = match?.photosRevealed || photosRevealed;

  useEffect(() => {
    Animated.spring(slideUpAnim, {
      toValue: 0,
      friction: 8,
      useNativeDriver: true,
    }).start();
  }, []);

  const handleSendVoice = (duration: number) => {
    sendVoiceMessage(matchId, duration);
    setTimeout(() => {
      flatListRef.current?.scrollToEnd({ animated: true });
    }, 100);
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" />
      <LinearGradient
        colors={['#FFF0F8', '#FFF5F9'] as [string, string]}
        style={styles.headerGradient}
      >
        <View style={styles.header}>
          <TouchableOpacity
            onPress={() => navigation.goBack()}
            style={styles.backBtn}
          >
            <Ionicons name="chevron-back" size={24} color={Colors.primary} />
          </TouchableOpacity>

          <View style={styles.headerCenter}>
            {currentPhotosRevealed ? (
              <Image source={{ uri: photoUrl }} style={styles.headerAvatar} />
            ) : (
              <LinearGradient
                colors={Colors.gradientPrimary as unknown as [string, string]}
                style={styles.headerAvatarMystery}
              >
                <Ionicons name="mic" size={16} color={Colors.white} />
              </LinearGradient>
            )}
            <View>
              <Text style={styles.headerName}>{userName}</Text>
              <Text style={styles.headerStatus}>
                {currentPhotosRevealed ? 'Photos revealed' : `${currentMessageCount}/10 to reveal`}
              </Text>
            </View>
          </View>

          <TouchableOpacity style={styles.moreBtn}>
            <Ionicons
              name="ellipsis-vertical"
              size={20}
              color={Colors.darkGray}
            />
          </TouchableOpacity>
        </View>
      </LinearGradient>

      {/* Photo reveal banner */}
      <PhotoRevealBanner
        messageCount={currentMessageCount}
        photosRevealed={currentPhotosRevealed}
        photoUrl={photoUrl}
        userName={userName}
      />

      {/* Voice-only notice */}
      {messages.length === 0 && (
        <View style={styles.voiceOnlyNotice}>
          <View style={styles.noticeIcon}>
            <Ionicons name="mic" size={24} color={Colors.primary} />
          </View>
          <Text style={styles.noticeTitle}>Voice-only chat</Text>
          <Text style={styles.noticeSubtext}>
            On Poppy, you connect through voice messages only.
            {'\n'}No typing - just your authentic voice!
          </Text>
          <View style={styles.noticeDivider}>
            {[Colors.primary, Colors.primaryLight, Colors.rose].map((c, i) => (
              <View key={i} style={[styles.noticeDot, { backgroundColor: c }]} />
            ))}
          </View>
        </View>
      )}

      {/* Messages list */}
      <FlatList
        ref={flatListRef}
        data={messages}
        renderItem={({ item }) => (
          <VoiceMessageBubble
            message={item}
            isMine={item.senderId === currentUser.id}
          />
        )}
        keyExtractor={item => item.id}
        contentContainerStyle={styles.messagesList}
        showsVerticalScrollIndicator={false}
        onContentSizeChange={() =>
          flatListRef.current?.scrollToEnd({ animated: false })
        }
      />

      {/* Voice record area */}
      <Animated.View
        style={[
          styles.recordArea,
          { transform: [{ translateY: slideUpAnim }] },
        ]}
      >
        <LinearGradient
          colors={['rgba(255,255,255,0)', 'rgba(255,255,255,0.95)', '#FFFFFF'] as [string, string, string]}
          style={styles.recordGradient}
        >
          <VoiceRecordButton onRecordComplete={handleSendVoice} />
        </LinearGradient>
      </Animated.View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.offWhite,
  },
  headerGradient: {
    paddingTop: Spacing.xxl + 10,
    paddingBottom: Spacing.sm,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.md,
    gap: Spacing.sm,
  },
  backBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(255,255,255,0.7)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerCenter: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  headerAvatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    borderWidth: 2,
    borderColor: Colors.primary,
  },
  headerAvatarMystery: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerName: {
    ...Typography.headlineSmall,
    color: Colors.black,
  },
  headerStatus: {
    ...Typography.caption,
    color: Colors.primary,
  },
  moreBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  voiceOnlyNotice: {
    alignItems: 'center',
    padding: Spacing.xl,
    gap: Spacing.sm,
  },
  noticeIcon: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: Colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
    ...Shadows.soft,
  },
  noticeTitle: {
    ...Typography.headlineMedium,
    color: Colors.primary,
  },
  noticeSubtext: {
    ...Typography.bodySmall,
    color: Colors.gray,
    textAlign: 'center',
  },
  noticeDivider: {
    flexDirection: 'row',
    gap: 6,
    marginTop: Spacing.sm,
  },
  noticeDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  messagesList: {
    paddingVertical: Spacing.md,
    paddingBottom: 160,
  },
  recordArea: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
  },
  recordGradient: {
    paddingTop: Spacing.xl,
    paddingBottom: Spacing.xxl,
    alignItems: 'center',
  },
});
