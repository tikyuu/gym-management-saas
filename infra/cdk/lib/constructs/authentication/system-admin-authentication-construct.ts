import {
  Duration,
  RemovalPolicy,
  aws_certificatemanager as acm,
  aws_cognito as cognito,
} from "aws-cdk-lib";
import { Construct } from "constructs";

interface SystemAdminAuthenticationConstructProps {
  edgeCertificate: acm.ICertificate;
  removalPolicy: RemovalPolicy;
  resourceNamePrefix: string;
  systemAdminAuthDomainName: string;
  systemAdminOAuthCallbackUrls: string[];
  systemAdminOAuthLogoutUrls: string[];
  systemAdminUserPoolDomainPrefix: string;
  userPoolDeletionProtection: boolean;
}

export class SystemAdminAuthenticationConstruct extends Construct {
  public readonly appClient: cognito.IUserPoolClient;
  public readonly customDomain: cognito.UserPoolDomain;
  public readonly userPool: cognito.IUserPool;

  constructor(
    scope: Construct,
    id: string,
    props: SystemAdminAuthenticationConstructProps,
  ) {
    super(scope, id);

    this.userPool = new cognito.UserPool(this, "SystemAdminUserPool", {
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      deletionProtection: props.userPoolDeletionProtection,
      featurePlan: cognito.FeaturePlan.ESSENTIALS,
      mfa: cognito.Mfa.REQUIRED,
      mfaSecondFactor: {
        otp: true,
        sms: false,
      },
      passwordPolicy: {
        minLength: 8,
        requireDigits: true,
        requireLowercase: true,
        requireSymbols: true,
        requireUppercase: true,
        tempPasswordValidity: Duration.days(7),
      },
      removalPolicy: props.removalPolicy,
      selfSignUpEnabled: false,
      signInAliases: {
        email: true,
      },
      signInCaseSensitive: false,
      userPoolName: `${props.resourceNamePrefix}-system-admin-user-pool`,
    });

    const userPoolDomain = this.userPool.addDomain(
      "SystemAdminUserPoolDomain",
      {
        cognitoDomain: {
          domainPrefix: props.systemAdminUserPoolDomainPrefix,
        },
        managedLoginVersion: cognito.ManagedLoginVersion.NEWER_MANAGED_LOGIN,
      },
    );

    this.customDomain = this.userPool.addDomain("SystemAdminCustomDomain", {
      customDomain: {
        certificate: props.edgeCertificate,
        domainName: props.systemAdminAuthDomainName,
      },
      managedLoginVersion: cognito.ManagedLoginVersion.NEWER_MANAGED_LOGIN,
    });

    this.appClient = new cognito.UserPoolClient(
      this,
      "SystemAdminAppClient",
      {
        accessTokenValidity: Duration.minutes(60),
        enableTokenRevocation: true,
        generateSecret: false,
        idTokenValidity: Duration.minutes(60),
        oAuth: {
          callbackUrls: props.systemAdminOAuthCallbackUrls,
          flows: {
            authorizationCodeGrant: true,
            implicitCodeGrant: false,
          },
          logoutUrls: props.systemAdminOAuthLogoutUrls,
          scopes: [cognito.OAuthScope.OPENID, cognito.OAuthScope.EMAIL],
        },
        preventUserExistenceErrors: true,
        refreshTokenRotationGracePeriod: Duration.seconds(10),
        refreshTokenValidity: Duration.hours(8),
        userPool: this.userPool,
        userPoolClientName: `${props.resourceNamePrefix}-system-admin-app-client`,
      },
    );

    const managedLoginBranding = new cognito.CfnManagedLoginBranding(
      this,
      "SystemAdminManagedLoginBranding",
      {
        clientId: this.appClient.userPoolClientId,
        useCognitoProvidedValues: true,
        userPoolId: this.userPool.userPoolId,
      },
    );

    managedLoginBranding.node.addDependency(userPoolDomain);
  }
}
