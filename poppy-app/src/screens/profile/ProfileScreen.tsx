import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  StatusBar,
  Switch,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Typography, Spacing, BorderRadius, Shadows } from '../../theme';
import { VoiceWaveform } from '../../components/VoiceWaveform';
import { VoiceRecordButton } from '../../components/VoiceRecordButton';
import { PoppyButton } from '../../components/PoppyButton';
import { useApp } from '../../context/AppContext';

export const ProfileScreen: React.FC = () => {
  const { currentUser, logout } = useApp();
  const [isPlayingIntro, setIsPlayingIntro] = useState(false);
  const [notifications, setNotifications] = useState(true);
  const [soundEffects, setSoundEffects] = useState(true);

  const menuSections = [
    {
      title: 'Account',
      items: [
        { icon: 'person-outline', label: 'Edit Profile', badge: null },
        { icon: 'mic-outline', label: 'Update Voice Intro', badge: 'NEW' },
        { icon: 'heart-outline', label: 'My Preferences', badge: null },
        { icon: 'shield-checkmark-outline', label: 'Verification', badge: null },
      ],
    },
    {
      title: 'Settings',
      items: [
        { icon: 'notifications-outline', label: 'Notifications', toggle: true, value: notifications, onToggle: setNotifications },
        { icon: 'volume-high-outline', label: 'Sound Effects', toggle: true, value: soundEffects, onToggle: setSoundEffects },
        { icon: 'lock-closed-outline', label: 'Privacy', badge: null },
        { icon: 'help-circle-outline', label: 'Help & Support', badge: null },
      ],
    },
  ];

  return (
    <LinearGradient
      colors={['#FFF0F8', '#FFFFFF', '#FFF5F9'] as [string, string, string]}
      style={styles.container}
    >
      <StatusBar barStyle="dark-content" />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Profile</Text>
          <TouchableOpacity style={styles.settingsBtn}>
            <Ionicons name="settings-outline" size={22} color={Colors.primary} />
          </TouchableOpacity>
        </View>

        {/* Profile card */}
        <View style={styles.profileCard}>
          <LinearGradient
            colors={Colors.gradientSunset as unknown as [string, string, string]}
            style={styles.profileCardGradient}
          >
            <View style={styles.profileImageContainer}>
              <Image
                source={{ uri: currentUser.photoUrl }}
                style={styles.profileImage}
              />
              <TouchableOpacity style={styles.editPhotoBtn}>
                <Ionicons name="camera" size={16} color={Colors.white} />
              </TouchableOpacity>
            </View>

            <Text style={styles.profileName}>
              {currentUser.name}, {currentUser.age}
            </Text>
            <View style={styles.locationRow}>
              <Ionicons name="location" size={14} color="rgba(255,255,255,0.8)" />
              <Text style={styles.profileLocation}>{currentUser.location}</Text>
            </View>

            {currentUser.verified && (
              <View style={styles.verifiedBadge}>
                <Ionicons name="checkmark-circle" size={14} color={Colors.white} />
                <Text style={styles.verifiedText}>Verified</Text>
              </View>
            )}
          </LinearGradient>
        </View>

        {/* Voice intro section */}
        <View style={styles.voiceIntroSection}>
          <View style={styles.sectionHeader}>
            <Ionicons name="mic" size={18} color={Colors.primary} />
            <Text style={styles.sectionTitle}>Your Voice Intro</Text>
          </View>

          <View style={styles.voiceIntroCard}>
            <TouchableOpacity
              onPress={() => setIsPlayingIntro(!isPlayingIntro)}
              style={styles.voicePlayBtn}
              activeOpacity={0.8}
            >
              <LinearGradient
                colors={Colors.gradientPrimary as unknown as [string, string]}
                style={styles.voicePlayGradient}
              >
                <Ionicons
                  name={isPlayingIntro ? 'pause' : 'play'}
                  size={20}
                  color={Colors.white}
                />
              </LinearGradient>
            </TouchableOpacity>

            <View style={styles.voiceIntroWaveform}>
              <VoiceWaveform
                isPlaying={isPlayingIntro}
                color={Colors.primary}
                height={32}
                barCount={20}
              />
            </View>

            <Text style={styles.voiceDuration}>
              {Math.floor(currentUser.voiceIntroDuration / 60)}:
              {(currentUser.voiceIntroDuration % 60).toString().padStart(2, '0')}
            </Text>
          </View>

          <TouchableOpacity style={styles.reRecordBtn}>
            <Ionicons name="refresh" size={16} color={Colors.primary} />
            <Text style={styles.reRecordText}>Re-record intro</Text>
          </TouchableOpacity>
        </View>

        {/* Interests */}
        <View style={styles.interestsSection}>
          <View style={styles.sectionHeader}>
            <Ionicons name="sparkles" size={18} color={Colors.primary} />
            <Text style={styles.sectionTitle}>Interests</Text>
          </View>
          <View style={styles.interestTags}>
            {currentUser.interests.map((interest, i) => (
              <View key={i} style={styles.interestTag}>
                <Text style={styles.interestText}>{interest}</Text>
              </View>
            ))}
            <TouchableOpacity style={styles.addInterestBtn}>
              <Ionicons name="add" size={18} color={Colors.primary} />
            </TouchableOpacity>
          </View>
        </View>

        {/* Menu sections */}
        {menuSections.map((section, sIndex) => (
          <View key={sIndex} style={styles.menuSection}>
            <Text style={styles.menuSectionTitle}>{section.title}</Text>
            {section.items.map((item, iIndex) => (
              <TouchableOpacity
                key={iIndex}
                style={styles.menuItem}
                activeOpacity={0.7}
              >
                <View style={styles.menuItemLeft}>
                  <View style={styles.menuIcon}>
                    <Ionicons
                      name={item.icon as any}
                      size={20}
                      color={Colors.primary}
                    />
                  </View>
                  <Text style={styles.menuLabel}>{item.label}</Text>
                </View>
                {'toggle' in item && item.toggle ? (
                  <Switch
                    value={item.value}
                    onValueChange={item.onToggle}
                    trackColor={{ false: Colors.lightGray, true: Colors.primaryLight }}
                    thumbColor={item.value ? Colors.primary : Colors.gray}
                  />
                ) : (
                  <View style={styles.menuItemRight}>
                    {'badge' in item && item.badge && (
                      <View style={styles.menuBadge}>
                        <Text style={styles.menuBadgeText}>{item.badge}</Text>
                      </View>
                    )}
                    <Ionicons name="chevron-forward" size={18} color={Colors.gray} />
                  </View>
                )}
              </TouchableOpacity>
            ))}
          </View>
        ))}

        {/* Logout */}
        <View style={styles.logoutSection}>
          <PoppyButton
            title="Sign Out"
            onPress={logout}
            variant="outline"
            size="medium"
          />
        </View>

        {/* App info */}
        <View style={styles.appInfo}>
          <Text style={styles.appName}>Poppy</Text>
          <Text style={styles.appVersion}>Version 1.0.0</Text>
          <Text style={styles.appTagline}>Where voices bloom into love</Text>
        </View>
      </ScrollView>
    </LinearGradient>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 100,
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
  settingsBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  profileCard: {
    marginHorizontal: Spacing.md,
    borderRadius: BorderRadius.xl,
    ...Shadows.strong,
    marginBottom: Spacing.lg,
  },
  profileCardGradient: {
    borderRadius: BorderRadius.xl,
    padding: Spacing.xl,
    alignItems: 'center',
  },
  profileImageContainer: {
    position: 'relative',
    marginBottom: Spacing.md,
  },
  profileImage: {
    width: 100,
    height: 100,
    borderRadius: 50,
    borderWidth: 3,
    borderColor: Colors.white,
  },
  editPhotoBtn: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: Colors.white,
  },
  profileName: {
    ...Typography.headlineLarge,
    color: Colors.white,
  },
  locationRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 4,
  },
  profileLocation: {
    ...Typography.bodySmall,
    color: 'rgba(255,255,255,0.8)',
  },
  verifiedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: Spacing.sm,
    backgroundColor: 'rgba(255,255,255,0.2)',
    paddingHorizontal: Spacing.md,
    paddingVertical: 4,
    borderRadius: BorderRadius.round,
  },
  verifiedText: {
    ...Typography.labelSmall,
    color: Colors.white,
  },
  voiceIntroSection: {
    marginHorizontal: Spacing.md,
    marginBottom: Spacing.lg,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    marginBottom: Spacing.sm,
  },
  sectionTitle: {
    ...Typography.labelLarge,
    color: Colors.primary,
  },
  voiceIntroCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
    backgroundColor: Colors.white,
    borderRadius: BorderRadius.lg,
    padding: Spacing.md,
    ...Shadows.soft,
  },
  voicePlayBtn: {},
  voicePlayGradient: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  voiceIntroWaveform: {
    flex: 1,
  },
  voiceDuration: {
    ...Typography.labelSmall,
    color: Colors.gray,
  },
  reRecordBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
    alignSelf: 'center',
    marginTop: Spacing.sm,
    paddingVertical: Spacing.xs,
  },
  reRecordText: {
    ...Typography.labelSmall,
    color: Colors.primary,
  },
  interestsSection: {
    marginHorizontal: Spacing.md,
    marginBottom: Spacing.lg,
  },
  interestTags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
  },
  interestTag: {
    backgroundColor: Colors.primarySoft,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.round,
    borderWidth: 1,
    borderColor: Colors.rose,
  },
  interestText: {
    ...Typography.labelSmall,
    color: Colors.primary,
  },
  addInterestBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: 2,
    borderColor: Colors.primary,
    borderStyle: 'dashed',
    alignItems: 'center',
    justifyContent: 'center',
  },
  menuSection: {
    marginHorizontal: Spacing.md,
    marginBottom: Spacing.lg,
  },
  menuSectionTitle: {
    ...Typography.labelMedium,
    color: Colors.gray,
    marginBottom: Spacing.sm,
    paddingLeft: Spacing.sm,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: Colors.white,
    padding: Spacing.md,
    borderRadius: BorderRadius.md,
    marginBottom: Spacing.xs,
    ...Shadows.soft,
  },
  menuItemLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
  },
  menuIcon: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: Colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  menuLabel: {
    ...Typography.bodyLarge,
    color: Colors.black,
  },
  menuItemRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  menuBadge: {
    backgroundColor: Colors.primary,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: BorderRadius.round,
  },
  menuBadgeText: {
    ...Typography.caption,
    color: Colors.white,
    fontSize: 9,
    fontWeight: '700',
  },
  logoutSection: {
    marginHorizontal: Spacing.xl,
    marginBottom: Spacing.lg,
  },
  appInfo: {
    alignItems: 'center',
    paddingVertical: Spacing.lg,
    gap: 4,
  },
  appName: {
    ...Typography.headlineMedium,
    color: Colors.primary,
  },
  appVersion: {
    ...Typography.caption,
    color: Colors.gray,
  },
  appTagline: {
    ...Typography.caption,
    color: Colors.rose,
    fontStyle: 'italic',
  },
});
