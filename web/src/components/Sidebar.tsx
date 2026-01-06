import { Box, VStack, HStack, Text, Button, Icon, useBreakpointValue } from "@chakra-ui/react";
import { FiHome, FiActivity, FiSettings, FiTerminal, FiTrendingUp } from "react-icons/fi";
import { PageType } from "../types";

interface SidebarProps {
  currentPage: PageType;
  setCurrentPage: (page: PageType) => void;
}

const menuItems = [
  { id: "dashboard" as PageType, label: "Dashboard", icon: FiHome },
  { id: "settings" as PageType, label: "Einstellungen", icon: FiSettings },
  { id: "stats" as PageType, label: "Statistiken", icon: FiTrendingUp },
  { id: "tasks" as PageType, label: "Aufgaben", icon: FiActivity },
  { id: "debug" as PageType, label: "Debug", icon: FiTerminal },
];

export const Sidebar = ({ currentPage, setCurrentPage }: SidebarProps) => {
  const isMobile = useBreakpointValue({ base: true, md: false });

  // Mobile: Horizontal sticky bar
  if (isMobile) {
    return (
      <Box
        position="sticky"
        top="70px"
        left={0}
        right={0}
        bg="gray.800"
        borderBottom="1px solid"
        borderColor="whiteAlpha.200"
        zIndex={998}
        overflowX="auto"
        className="mobile-nav"
      >
        <HStack spacing={0} py={2} px={3} minW="max-content">
          {menuItems.map((item) => (
            <Button
              key={item.id}
              variant={currentPage === item.id ? "solid" : "ghost"}
              colorScheme={currentPage === item.id ? "teal" : "gray"}
              size="sm"
              leftIcon={<Icon as={item.icon} />}
              onClick={() => setCurrentPage(item.id)}
              minW="fit-content"
              whiteSpace="nowrap"
              fontSize="xs"
            >
              {item.label}
            </Button>
          ))}
        </HStack>
      </Box>
    );
  }

  // Desktop: Vertical sidebar
  return (
    <Box className="sidebar">
      <VStack align="stretch" spacing={6} p={6}>
        <Box textAlign="center" py={4}>
          <Text fontSize="2xl" fontWeight="bold" className="gradient-text">
            PennerBot
          </Text>
          <Text fontSize="xs" color="gray.400" mt={1}>
            Dashboard
          </Text>
        </Box>

        <VStack align="stretch" spacing={2} className="fade-in">
          {menuItems.map((item, index) => (
            <Button
              key={item.id}
              variant={currentPage === item.id ? "solid" : "ghost"}
              colorScheme={currentPage === item.id ? "teal" : "gray"}
              justifyContent="flex-start"
              leftIcon={<Icon as={item.icon} boxSize={5} />}
              onClick={() => setCurrentPage(item.id)}
              size="lg"
              _hover={{ bg: "whiteAlpha.200", transform: "translateX(4px)" }}
              transition="all 0.2s"
              style={{ animationDelay: `${index * 0.05}s` }}
              fontWeight={currentPage === item.id ? "bold" : "normal"}
            >
              {item.label}
            </Button>
          ))}
        </VStack>
      </VStack>
    </Box>
  );
};
