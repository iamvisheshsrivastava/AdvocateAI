// Regression test for issue #32: a network failure while loading the case
// workspace must not leave the user stuck on an infinite spinner. Instead,
// an error state with a retry action must be shown.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'package:test_app/case_workspace_page.dart';

class _AlwaysFailingClient extends http.BaseClient {
  int requestCount = 0;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    requestCount++;
    throw Exception('Simulated network failure');
  }
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'shows a retry button instead of an infinite spinner when every '
    'workspace request fails',
    (WidgetTester tester) async {
      final failingClient = _AlwaysFailingClient();

      await http.runWithClient(
        () async {
          await tester.pumpWidget(
            const MaterialApp(
              home: CaseWorkspacePage(caseId: 1, currentUserId: 1),
            ),
          );

          // Let the initial _loadWorkspace() future (and its Future.wait)
          // resolve after every request throws.
          for (var i = 0; i < 10; i++) {
            await tester.pump(const Duration(milliseconds: 50));
          }

          // No infinite spinner: the loading indicator must be gone.
          expect(find.byType(CircularProgressIndicator), findsNothing);

          // An actionable error state must be visible instead.
          expect(find.byIcon(Icons.error_outline), findsOneWidget);
          expect(find.widgetWithText(ElevatedButton, 'Retry'), findsOneWidget);

          final requestsBeforeRetry = failingClient.requestCount;
          expect(requestsBeforeRetry, greaterThan(0));

          // Tapping retry triggers another load attempt.
          await tester.tap(find.widgetWithText(ElevatedButton, 'Retry'));
          for (var i = 0; i < 10; i++) {
            await tester.pump(const Duration(milliseconds: 50));
          }

          expect(failingClient.requestCount, greaterThan(requestsBeforeRetry));
          // Still shows the error state rather than hanging on a spinner.
          expect(find.byType(CircularProgressIndicator), findsNothing);
          expect(find.widgetWithText(ElevatedButton, 'Retry'), findsOneWidget);
        },
        () => failingClient,
      );
    },
  );
}
